# metamk

**A minimal framework for defining phase structure around a main action.**

**metamk** is a minimalistic phase-structured execution framework designed to improve **readability**, **traceability**, and **exception clarity** in procedural or test-like code.

At its core, `metamk` provides two layers:

- **`Mk`** — a _stateless_, lightweight wrapper for visually structured, traceable code.  
- **`Mark`** — a _stateful_, strict phase controller with ordering validation and error hooks.

This document focuses on **`Mk`**, the simpler and most frequently used layer.  
`Mk` does not enforce any runtime order or state; instead, it serves as a **visual and structural aid** while ensuring that stack traces clearly show which phase failed.

---

## ✨ Features

- **Stateless** — No runtime phase tracking or locking. Functions execute immediately.
- **Readable structure** — Provides named phase methods like `setup`, `before`, `MAIN`, etc.
- **Traceable errors** — When an exception occurs, the traceback includes the phase call (e.g., `after()`, `cleanup()`).
- **Synchronous & asynchronous support** —  
  Use `Mk` for normal code, or `Mk.a` for async workflows.
- **No external dependencies** — 100% Python standard library.

---

## 🧩 Phase Overview

| Phase | Method | Purpose |
|--------|---------|----------|
| **Invariant** | `invariant()` | Validate preconditions or invariant properties |
| **Setup** | `setup()` | Prepare environment or test context |
| **Before** | `before()` | Perform pre-run checks |
| **Act** | `MAIN()` | Execute the main action under test |
| **Cleanup** | `cleanup()` | Release temporary resources |
| **After** | `after()` | Verify results or postconditions |
| **Final** | `final()` | Wrap-up, log, or finalize |

Each phase can be expressed as a block (`with Mk.as_setup_block():`) or as a direct call (`Mk.setup(fn)`).

---

## 🚀 Basic Example

```python
from metamk import Mk

def test_example():
    with Mk.as_setup_block():
        data = Mk.setup(lambda: {"x": 1, "y": 2})

    with Mk.as_before_block():
        Mk.before(lambda: data["x"] < data["y"])

    with Mk.as_MAIN_block():
        result = Mk.MAIN(data["x"] + data["y"])

    with Mk.as_cleanup_block():
        Mk.cleanup(lambda: data.clear())

    with Mk.as_after_block():
        Mk.after(lambda: result == 3)

    with Mk.as_final_block():
        Mk.final(lambda: print("Test completed successfully!"))
````

**Output:**

```
Test completed successfully!
```

If a check fails (for example, `Mk.after(lambda: result == 3)` returning `False`),
a clear traceback is shown:

```
Traceback (most recent call last):
  File "test_example.py", line 12, in test_example
    Mk.after(lambda: result == 3)
  File ".../metamk.py", line 530, in after
    cls._evaluate_fn(fn())
RuntimeError: evaluation failed.
```

---

## ⚙️ Async Example

```python
from metamk import Mk

async def test_async_example():
    async with Mk.a.as_setup_block():
        data = await Mk.a.setup(async_prepare_data())

    async with Mk.a.as_before_block():
        await Mk.a.before(check_condition(data))

    async with Mk.a.as_MAIN_block():
        result = Mk.MAIN(await run_action(data))

    async with Mk.a.as_cleanup_block():
        await Mk.a.cleanup(async_cleanup(data))

    async with Mk.a.as_after_block():
        await Mk.a.after(validate_result(result))

    async with Mk.a.as_final_block():
        await Mk.a.final(async_log_result(result))
```

---

## 🪶 Design Philosophy

`Mk` is intentionally *a do-nothing wrapper* — it executes your code directly without altering behavior or enforcing phase order.

Each method serves a simple purpose:

* `setup(fn)` → executes `fn()` and returns its result.
* `before(fn)` → executes `fn()`; raises `RuntimeError` if result is falsy.
* `MAIN(v)` → returns the given value as-is.
* `cleanup(fn)` / `final(fn)` → execute `fn()` and return result.
* `as_*_block()` → creates a visual structure, no runtime side effects.

This structure ensures:

* Code remains **clean and expressive**.
* Tracebacks remain **phase-aware**.
* Your test or procedure flow is **visually and semantically segmented**.

---

## 🧠 Why “metamk”?

The prefix **“meta”** reflects the framework’s philosophy —
`metamk` is not a test runner or validator itself; it’s **a meta-layer** that helps structure, visualize, and debug complex procedural flows.

---

## 🔍 Comparison: `Mk` vs. `Mark`

| Feature                                | `Mk`                                 | `Mark`                          |
| -------------------------------------- | ------------------------------------ | ------------------------------- |
| Stateful phase control                 | ❌ No                                 | ✅ Yes                           |
| Thread safety                          | ❌ No                                 | ✅ Yes                           |
| Phase transition validation            | ❌ No                                 | ✅ Yes                           |
| Custom hooks (`on_result`, `on_error`) | ❌ No                                 | ✅ Yes                           |
| Traceback phase info                   | ✅ Yes                                | ✅ Yes                           |
| Use case                               | Readable test flow, simple scripting | Strict procedural orchestration |

---

## 🧭 Recommended Use Cases

* Structuring test or validation flows in readable steps.
* Tracking where an exception occurred (via phase name in traceback).
* Asynchronous step-based testing or workflows.
* Lightweight visual separation of procedural code.
---

Installation

pip
```bash
pip install metamk
```

github
```bash
pip install git+https://github.com/minoru-jp/metamk.git
```

---

## Status

This project is in **very early development (alpha stage)**.  
APIs and behavior may change without notice.

---

## License

MIT License © 2025 minoru_jp

