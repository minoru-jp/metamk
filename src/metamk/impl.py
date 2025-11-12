from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from enum import Enum
import threading
from typing import Any, AsyncGenerator, Awaitable, Callable, Generator, Iterator, TypeVar

T = TypeVar("T")

class Phase(Enum):

    _INIT = 0

    SETUP = 1
    BEFORE = 2
    ACT = 3
    CLEANUP = 4
    AFTER = 5
    FINAL = 6
    _TERMINATED = 7

    INVARIANT = -1

class PhaseError(Exception):
    def __init__(self, f: Phase, t: Phase, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.phase_from = f
        self.phase_to = t

class _OrderingMethod(Enum):
    # All member must correspound to each Phase member value 
    # for reverse lookup from value to Phase member.
    INIT = 0

    SETUP = 1
    BEFORE = 2
    ACT = 3
    CLEANUP = 4
    AFTER = 5
    FINAL = 6
    TERMINATED = 7

    INVARIANT = -1

    def is_required_act_called(self):
        return self in (_OrderingMethod.CLEANUP, _OrderingMethod.AFTER)
    
    def to_phase(self) -> Phase:
        # Perform reverse lookup to corresponding Phase member
        try:
            return Phase(self.value)
        except ValueError:
            raise RuntimeError("Bug: Possibly an uncorresponding member value.")


@dataclass(slots = True)
class _OrderState:
    _thread_lock: Any = field(default_factory = threading.Lock)
    current: _OrderingMethod = field(default = _OrderingMethod.INIT)
    is_act_called: bool = field(default = False)

    def to(self, nxt: _OrderingMethod) -> None:
        """No use asyncio.Lock, so event loop will stop during this process."""
        with self._thread_lock:
            if nxt == _OrderingMethod.INVARIANT:
                if self.current != _OrderingMethod.TERMINATED:
                    return
            if nxt.value < self.current.value:
                raise PhaseError(
                    self.current.to_phase(), nxt.to_phase(),
                    "The call order is invalid. " +
                    f"{nxt.name} cannot be called after {self.current.name}."
                )
            if nxt.is_required_act_called() and not self.is_act_called:
                raise PhaseError(
                    self.current.to_phase(), nxt.to_phase(),
                    "The call order is invalid. " +
                    f"{nxt.name} cannot be called before {_OrderingMethod.ACT.name}."
                )
            self.current = nxt
            self.is_act_called = nxt == _OrderingMethod.ACT

_CALL = Callable | Awaitable | None

class Mark:
    """Phase methods for asynchronous functions are available under Mark.a.
    The ACT method exists only on Mark, not on Mark.a;
    in async code, use mark.ACT(await obj.method()).
    """

    def __init__(self):
        self._order_state = _OrderState()
        self._async_mark = _AsyncMark(self)

    def on_error_in_phase_block(self, phase: Phase, obj: _CALL, e: Exception):
        """Called when an exception occurs inside a phase block.

        This method is a notification hook. If overridden and it raises,
        the exception propagates to the caller."""
        return # default implementation
    
    def on_phase_transition_error(self, e: PhaseError, obj: _CALL):
        """Called when an invalid phase transition is detected.

        This method is a notification hook. If overridden and it raises,
        the exception propagates to the caller."""
        return # default implementation
    
    def on_result(self, phase: Phase, obj: _CALL, r: Any) -> bool:
        """Called with the result returned by a phase function.

        Return True for success or False to trigger on_negative()."""
        return bool(r) # default implementation
    
    def on_positive(self, phase: Phase, obj: _CALL, r: Any) -> None:
        """Called when on_result() returns True.

        Default behavior continues processing."""
        return # default implementation

    def on_negative(self, phase: Phase, obj: _CALL , r: Any) -> None:
        """Called when on_result() returns False.

        Default behavior raises RuntimeError to stop processing."""
        # default implementation
        raise RuntimeError(f"evaluation failed on {phase.name}") 
    

    @property
    def a(self) -> "_AsyncMark":
        return self._async_mark


    def invariant(self, fn: Callable[[], bool]) -> None:
        return self._delegate_to_evaluate_fn(_OrderingMethod.INVARIANT, fn)
        
    def setup(self, fn: Callable[[], T]) -> T:
        return self._delegate_to_call_fn(_OrderingMethod.SETUP, fn)

    def before(self, fn: Callable[[], bool]) -> None:
        self._delegate_to_evaluate_fn(_OrderingMethod.BEFORE, fn)

    def MAIN(self, v: T) -> T:
        """Unlike other phase methods, this method takes a value directly instead of a callable."""
        self._order_state.to(_OrderingMethod.ACT)
        return v
    
    def cleanup(self, fn: Callable[[], T]) -> T:
        return self._delegate_to_call_fn(_OrderingMethod.CLEANUP, fn)

    def after(self, fn: Callable[[], bool]) -> None:
        self._delegate_to_evaluate_fn(_OrderingMethod.AFTER, fn)
    
    def final(self, fn: Callable[[], T]) -> T:
        return self._delegate_to_call_fn(_OrderingMethod.FINAL, fn)
    
    def invoke(self, fn: Callable[[], T]) -> T:
        """Invoke the given callable at any time, without triggering any phase transition or state change."""
        return fn()
    

    @contextmanager
    def as_block(self) -> Iterator[None]:
        """This block must be entered before any other phase methods.
        Once this block exits, no further phase methods can be called."""
        try:
            try:
                if self._order_state.current != _OrderingMethod.INIT:
                    # raise to attach a proper traceback 
                    # before handling the exception
                    raise PhaseError(
                        self._order_state.current.to_phase(),
                        _OrderingMethod.INIT.to_phase(),
                        f"This block must be started before any phases."
                    )
            except PhaseError as e: # catch immediately
                self.on_phase_transition_error(e, None)
                raise e
            yield None
        finally:
            try:
                self._order_state.to(_OrderingMethod.TERMINATED)
            except PhaseError as e:
                self.on_phase_transition_error(e, None)
            if not self._order_state.is_act_called:
                raise RuntimeError("This test block ended without calling ACT.")
    
    @contextmanager
    def as_invariant_block(self) -> Generator[None]:
        with self._ordering_block_process(_OrderingMethod.INVARIANT, None):
            yield

    @contextmanager
    def as_setup_block(self) -> Generator[None]:
        with self._ordering_block_process(_OrderingMethod.SETUP, None):
            yield

    @contextmanager
    def as_before_block(self) -> Generator[None]:
        with self._ordering_block_process(_OrderingMethod.BEFORE, None):
            yield

    @contextmanager
    def as_MAIN_block(self) -> Generator[None]:
        with self._ordering_block_process(_OrderingMethod.ACT, None):
            yield
    
    @contextmanager
    def as_cleanup_block(self) -> Generator[None]:
        with self._ordering_block_process(_OrderingMethod.CLEANUP, None):
            yield
    
    @contextmanager
    def as_after_block(self) -> Generator[None]:
        with self._ordering_block_process(_OrderingMethod.AFTER, None):
            yield

    @contextmanager
    def as_final_block(self) -> Generator[None]:
        with self._ordering_block_process(_OrderingMethod.FINAL, None):
            yield


    def _delegate_to_call_fn(self, order: _OrderingMethod, fn: Callable[[], T]) -> T:
        with self._ordering_block_process(order, fn):
            return fn()

    def _delegate_to_evaluate_fn(self, order: _OrderingMethod, fn: Callable):
        with self._ordering_block_process(order, fn):
            self._evaluate_fn(order, fn)

    @contextmanager
    def _ordering_block_process(
        self, order: _OrderingMethod, fn: Callable | None
    ) -> Iterator[None]:
        try:
            try:
                self._order_state.to(order)
            except PhaseError as e:
                self.on_phase_transition_error(e, fn)
                raise e
            yield None
        except Exception as e:
            self.on_error_in_phase_block(order.to_phase(), fn, e)
            raise e
        finally:
            pass
    
    def _evaluate_fn(self, order: _OrderingMethod, fn: Callable) -> None:
        p = order.to_phase()
        r = fn()
        flag = self.on_result(p , fn, r)
        if flag:
            self.on_positive(p, fn, r)
        else:
            self.on_negative(p, fn, r)

class _AsyncMark:

    def __init__(self, parent: Mark):
        self._parent = parent

    async def invariant(self, awaitable: Awaitable[bool]) -> None:
        return await self._delegate_to_evaluate_awaitable(
            _OrderingMethod.INVARIANT, awaitable
        )
        
    async def setup(self, awaitable: Awaitable[T]) -> T:
        return await self._delegate_to_call_awaitable(
            _OrderingMethod.SETUP, awaitable
        )

    async def before(self, awaitable: Awaitable[bool]) -> None:
        await self._delegate_to_evaluate_awaitable(
            _OrderingMethod.BEFORE, awaitable
        )
    
    async def cleanup(self, awaitable: Awaitable[T]) -> T:
        return await self._delegate_to_call_awaitable(
            _OrderingMethod.CLEANUP, awaitable
        )

    async def after(self, awaitable: Awaitable[bool]) -> None:
        await self._delegate_to_evaluate_awaitable(
            _OrderingMethod.AFTER, awaitable
        )
    
    async def final(self, awaitable: Awaitable[T]) -> T:
        return await self._delegate_to_call_awaitable(
            _OrderingMethod.FINAL, awaitable
        )
    
    async def invoke(self, awaitable: Awaitable[T]) -> T:
        """Await the given awaitable at any time, without triggering any phase transition or state change."""
        return await awaitable


    @asynccontextmanager
    async def as_block(self) -> AsyncGenerator[None, None]:
        """This block must be entered before any other phase methods.
        Once this block exits, no further phase methods can be called."""
        try:
            try:
                if self._parent._order_state.current != _OrderingMethod.INIT:
                    # raise to attach a proper traceback 
                    # before handling the exception
                    raise PhaseError(
                        self._parent._order_state.current.to_phase(),
                        _OrderingMethod.INIT.to_phase(),
                        f"This block must be started before any phases."
                    )
            except PhaseError as e: # catch immediately
                self._parent.on_phase_transition_error(e, None)
                raise e
            yield None
        finally:
            try:
                self._parent._order_state.to(_OrderingMethod.TERMINATED)
            except PhaseError as e:
                self._parent.on_phase_transition_error(e, None)
                raise e
            if not self._parent._order_state.is_act_called:
                raise RuntimeError(
                    "This test block ended async without calling ACT."
                )
    
    @asynccontextmanager
    async def as_invariant_block(self) -> AsyncGenerator[None, None]:
        async with self._ordering_block_process(_OrderingMethod.INVARIANT, None):
            yield

    @asynccontextmanager
    async def as_setup_block(self) -> AsyncGenerator[None, None]:
        async with self._ordering_block_process(_OrderingMethod.SETUP, None):
            yield

    @asynccontextmanager
    async def as_before_block(self) -> AsyncGenerator[None, None]:
        async with self._ordering_block_process(_OrderingMethod.BEFORE, None):
            yield

    @asynccontextmanager
    async def as_MAIN_block(self) -> AsyncGenerator[None, None]:
        async with self._ordering_block_process(_OrderingMethod.ACT, None):
            yield
    
    @asynccontextmanager
    async def as_cleanup_block(self) -> AsyncGenerator[None, None]:
        async with self._ordering_block_process(_OrderingMethod.CLEANUP, None):
            yield
    
    @asynccontextmanager
    async def as_after_block(self) -> AsyncGenerator[None, None]:
        async with self._ordering_block_process(_OrderingMethod.AFTER, None):
            yield

    @asynccontextmanager
    async def as_final_block(self) -> AsyncGenerator[None, None]:
        async with self._ordering_block_process(_OrderingMethod.FINAL, None):
            yield


    async def _delegate_to_call_awaitable(
            self, order: _OrderingMethod, awaitable: Awaitable[T]
    ) -> T:
        async with self._ordering_block_process(order, awaitable):
            return await awaitable

    async def _delegate_to_evaluate_awaitable(
            self, order: _OrderingMethod, awaitable: Awaitable
    ) -> None:
        async with self._ordering_block_process(order, awaitable):
            await self._evaluate_awaitable(order, awaitable)

    @asynccontextmanager
    async def _ordering_block_process(
            self, order: _OrderingMethod, awaitable: Awaitable | None
    ) -> AsyncGenerator[None, None]:
        try:
            try:
                self._parent._order_state.to(order)
            except PhaseError as e:
                self._parent.on_phase_transition_error(e, awaitable)
                raise e
            yield None
        except Exception as e:
            self._parent.on_error_in_phase_block(order.to_phase(), awaitable, e)
            raise e
        finally:
            pass
    
    async def _evaluate_awaitable(
            self, order: _OrderingMethod, awaitable: Awaitable
    ) -> None:
        p = order.to_phase()
        r = await awaitable
        flag = self._parent.on_result(p , awaitable, r)
        if flag:
            self._parent.on_positive(p, awaitable, r)
        else:
            self._parent.on_negative(p, awaitable, r)


class _AsyncMk:

    @classmethod
    async def invariant(cls, awaitable: Awaitable[bool]) -> None:
        Mk._evaluate_fn(await awaitable)
    
    @classmethod
    async def setup(cls, awaitable: Awaitable[T]) -> T:
        return await awaitable

    @classmethod
    async def before(cls, awaitable: Awaitable[bool]) -> None:
        Mk._evaluate_fn(await awaitable)
    
    @classmethod
    async def cleanup(cls, awaitable: Awaitable[T]) -> T:
        return await awaitable

    @classmethod
    async def after(cls, awaitable: Awaitable[bool]) -> None:
        Mk._evaluate_fn(await awaitable)
    
    @classmethod
    async def final(cls, awaitable: Awaitable[T]) -> T:
        return await awaitable
    
    @classmethod
    async def invoke(cls, awaitable: Awaitable[T]) -> T:
        return await awaitable

    @classmethod
    @asynccontextmanager
    async def as_invariant_block(cls) -> AsyncGenerator[None, None]:
        yield

    @classmethod
    @asynccontextmanager
    async def as_setup_block(cls) -> AsyncGenerator[None, None]:
        yield

    @classmethod
    @asynccontextmanager
    async def as_before_block(cls) -> AsyncGenerator[None, None]:
        yield

    @classmethod
    @asynccontextmanager
    async def as_MAIN_block(cls) -> AsyncGenerator[None, None]:
        yield
    
    @classmethod
    @asynccontextmanager
    async def as_cleanup_block(cls) -> AsyncGenerator[None, None]:
        yield
    
    @classmethod
    @asynccontextmanager
    async def as_after_block(cls) -> AsyncGenerator[None, None]:
        yield

    @classmethod
    @asynccontextmanager
    async def as_final_block(cls) -> AsyncGenerator[None, None]:
        yield


class Mk:
    a = _AsyncMk

    @classmethod
    def _evaluate_fn(cls, result) -> None:
        if not result:
            raise RuntimeError("evaluation failed.")

    @classmethod
    def invariant(cls, fn: Callable[[], bool]) -> None:
        cls._evaluate_fn(fn())
        
    @classmethod
    def setup(cls, fn: Callable[[], T]) -> T:
        return fn()

    @classmethod
    def before(cls, fn: Callable[[], bool]) -> None:
        cls._evaluate_fn(fn())

    @classmethod
    def MAIN(cls, v: T) -> T:
        return v
    
    @classmethod
    def cleanup(cls, fn: Callable[[], T]) -> T:
        return fn()

    @classmethod
    def after(cls, fn: Callable[[], bool]) -> None:
        cls._evaluate_fn(fn())
    
    @classmethod
    def final(cls, fn: Callable[[], T]) -> T:
        return fn()
    
    @classmethod
    def invoke(cls, fn: Callable[[], T]) -> T:
        return fn()
    

    @classmethod
    @contextmanager
    def as_invariant_block(cls) -> Generator[None]:
        yield

    @classmethod
    @contextmanager
    def as_setup_block(cls) -> Generator[None]:
        yield

    @classmethod
    @contextmanager
    def as_before_block(cls) -> Generator[None]:
        yield

    @classmethod
    @contextmanager
    def as_MAIN_block(cls) -> Generator[None]:
        yield
    
    @classmethod
    @contextmanager
    def as_cleanup_block(cls) -> Generator[None]:
        yield
    
    @classmethod
    @contextmanager
    def as_after_block(cls) -> Generator[None]:
        yield

    @classmethod
    @contextmanager
    def as_final_block(cls) -> Generator[None]:
        yield


