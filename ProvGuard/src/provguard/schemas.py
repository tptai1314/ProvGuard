"""Typed objects corresponding to the paper's Definitions 1, 2, 6, and 8."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any


class RegionKind(str, Enum):
    NODE = "node"
    TILE = "tile"


class WindowType(str, Enum):
    APPLICATION = "application"
    OVERLAY = "overlay"
    SHADE = "shade"
    IME = "ime"
    SYSTEM = "system"
    SDK_SURFACE = "sdk-surface"


class ActionOp(str, Enum):
    TAP = "tap"
    LONG_PRESS = "long_press"
    TYPE = "type"
    SWIPE = "swipe"
    BACK = "back"
    HOME = "home"
    LAUNCH = "launch"
    FINISH = "finish"


class SinkClass(str, Enum):
    SEND = "send"
    PAY = "pay"
    INSTALL = "install"
    GRANT = "grant"
    DELETE = "delete"
    SHARE = "share"
    TYPE_UNTRUSTED = "type-untrusted"


class EquivalenceMode(str, Enum):
    CONTROL = "control"
    STRICT = "strict"


class GateDecision(str, Enum):
    PASS = "pass"
    ESCALATE = "escalate"


class DispatchStatus(str, Enum):
    DELIVERED = "delivered"
    REOBSERVE = "reobserve"
    DROPPED = "dropped"


@dataclass(frozen=True)
class BoundingBox:
    left: float
    top: float
    right: float
    bottom: float

    def __post_init__(self) -> None:
        if self.right < self.left or self.bottom < self.top:
            raise ValueError("BoundingBox edges must be ordered")

    @property
    def area(self) -> float:
        return max(0.0, self.right - self.left) * max(0.0, self.bottom - self.top)

    def contains(self, x: float, y: float) -> bool:
        return self.left <= x <= self.right and self.top <= y <= self.bottom


@dataclass(frozen=True)
class Geometry:
    bounds: BoundingBox
    z_order: int = 0
    class_name: str = ""
    clickable: bool = False
    editable: bool = False
    touchable: bool = False


@dataclass(frozen=True)
class ProvenanceRecord:
    """Paper Eq. (1): r(rho)=(uid,wtype,org,snd,sens,perc)."""

    uid: int
    window_type: WindowType
    web_origin: str | None = None
    notification_sender: str | None = None
    notification_sensitive: bool = False
    perceivable: bool = True


@dataclass(frozen=True)
class Binding:
    """Observed target binding beta=(window token,node id,digest,owner uid)."""

    window_token: str
    node_id: str | None
    digest: str | None
    owner_uid: int


@dataclass(frozen=True)
class Region:
    region_id: str
    kind: RegionKind
    content: str
    geometry: Geometry
    provenance: ProvenanceRecord
    label: IntegrityLabel
    binding: Binding | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def masked(self, placeholder: str) -> Region:
        return replace(self, content=placeholder)


@dataclass(frozen=True)
class Observation:
    observation_id: str
    step: int
    regions: tuple[Region, ...]
    display_width: int = 1080
    display_height: int = 2400

    def region(self, region_id: str) -> Region | None:
        return next((r for r in self.regions if r.region_id == region_id), None)


@dataclass(frozen=True)
class Action:
    """Paper Definition 6: action triple plus an explicit observation/sink annotation."""

    op: ActionOp
    observation_id: str
    target_region_id: str | None = None
    coordinates: tuple[float, float] | None = None
    argument: str | None = None
    sink_class: SinkClass | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.target_region_id is not None and self.coordinates is not None:
            raise ValueError("Action target must be a node or coordinates, not both")


@dataclass(frozen=True)
class Transcript:
    """Paper Definition 8: OS-held task, dispatched actions, and observations."""

    task: str
    actions: tuple[Action, ...] = ()
    observations: tuple[Observation, ...] = ()

    def observation(self, observation_id: str) -> Observation:
        for observation in self.observations:
            if observation.observation_id == observation_id:
                return observation
        raise KeyError(f"Unknown observation id: {observation_id}")

    def append_action(self, action: Action) -> Transcript:
        return replace(self, actions=self.actions + (action,))

    def append_observation(self, observation: Observation) -> Transcript:
        return replace(self, observations=self.observations + (observation,))


@dataclass(frozen=True)
class LiveWindow:
    token: str
    owner_uid: int
    touchable_bounds: tuple[BoundingBox, ...]
    z_order: int
    nodes: dict[str, str] = field(default_factory=dict)  # node id -> current digest

    def touchable_at(self, x: float, y: float) -> bool:
        return any(bounds.contains(x, y) for bounds in self.touchable_bounds)


@dataclass(frozen=True)
class GateResult:
    decision: GateDecision
    protected: bool
    support_fraction: float | None
    equivalent_trials: int
    trials: int
    untrusted_region_ids: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class DispatchResult:
    status: DispatchStatus
    reason: str
    window_token: str | None = None


# Delayed import keeps the enum in a focused module without a runtime cycle.
from .lattice import IntegrityLabel  # isort: skip

