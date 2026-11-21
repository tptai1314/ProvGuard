"""ProvGuard formal reference model and experiment harness."""

from .binder import DispatchBinder
from .gate import CausalGate
from .labeling import DefaultLabelingPolicy
from .lattice import IntegrityLabel
from .pipeline import ProvGuardPipeline

__all__ = [
    "CausalGate",
    "DefaultLabelingPolicy",
    "DispatchBinder",
    "IntegrityLabel",
    "ProvGuardPipeline",
]

__version__ = "0.1.0"

