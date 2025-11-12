"""metamk - A minimal framework for defining phase structure around a main action.

metamk structures execution into clear, explicit phases without adding control logic.
"""

from metamk.impl import Mk, Mark, Phase, PhaseError

__all__ = ["Mk", "Mark", "Phase", "PhaseError"]
