# metamk

**A minimal framework for defining phase structure around a main action.**

Inspired by Arrange–Act–Assert testing pattern and Design by Contract,  
metamk structures execution into clear, explicit phases without adding control logic.

It separates the main processing phase from setup, checks, and cleanup,  
and provides both synchronous and asynchronous APIs.

```python
from metamk import Mark

mark = Mark()

async with mark.a.as_block():
    mark.a.setup(async_setup())
    mark.a.before(async_check())

    result = mark.MAIN(await async_action())
    
    mark.a.after(async_validate())
    mark.a.final(async_cleanup())
````

The main action (`MAIN`) always belongs to `Mark`,
while async phase methods are available under `Mark.a`.

Synchronous use is also supported:

```python
with mark.as_block():
    mark.setup(lambda: print("setup"))
    mark.before(lambda: True)

    result = mark.MAIN("main action")
    
    mark.after(lambda: True)
    mark.final(lambda: print("done"))
```

When you want to group multiple operations within the same phase,  
you can use the corresponding `as_*_block()` context instead of a single method call.

```python
async with mark.a.as_block():
    async with mark.a.as_setup_block():
        await obj.setup()

    async with mark.a.as_before_block():
        await obj.pre_check()

    async with mark.a.as_MAIN_block():
        result = await obj.main_action()
        print(f"MAIN result: {result}")

    async with mark.a.as_after_block():
        await obj.validate()

    async with mark.a.as_final_block():
        await obj.cleanup()
```

---

## Phase Management

This module provides a safe and flexible mechanism for managing the execution state (phase) of a process.  
Phases generally progress in the following order:

```
INIT → SETUP → BEFORE → MAIN → CLEANUP → AFTER → FINAL → TERMINATED
```

However, **strict sequential progression is not enforced**.  
While phases are expected to move “forward” in order,  
it is allowed to call the same phase method or block multiple times in succession,  
or to skip intermediate phases — for example, jumping directly to `FINAL` if necessary.

Additionally, the `CLEANUP` and `AFTER` phases require that the `MAIN` phase has already been executed.  
If this condition is not met, or if the phase order is reversed, a `PhaseError` will be raised.

The `INVARIANT` phase is a flexible phase that can be invoked after **any phase**,  
as long as the process has not reached the `TERMINATED` state.

Furthermore, by using `Mark.invoke`, you can perform a simple, standalone call  
that is completely independent of the phase system.



