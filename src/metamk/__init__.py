"""metamk - divide test code into PREPARE / MAIN / VERIFY phases.

An exception that passes through a phase block gets the phase name recorded on
it, so a failure shows *which phase* it happened in. At runtime the blocks do
nothing else: they never change control flow and never swallow or replace
exceptions.
"""

from metamk._core import Mk, phase_of

__all__ = ["Mk", "phase_of"]
