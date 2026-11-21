"""Reference Label Service policy from paper Definition 5 and Algorithm 1."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace

from .lattice import IntegrityLabel, join_all
from .schemas import ProvenanceRecord, Region, WindowType


@dataclass(frozen=True)
class DefaultLabelingPolicy:
    target_app_uid: int
    system_uids: frozenset[int] = frozenset({0, 1000})
    system_packages: frozenset[str] = frozenset({"android", "com.android.systemui"})

    def label(
        self,
        record: ProvenanceRecord,
        *,
        user_input: bool = False,
        developer_untrusted_annotation: bool = False,
    ) -> IntegrityLabel:
        """Apply Lambda_0 in its stated order of precedence."""

        if user_input:
            return IntegrityLabel.USER
        if developer_untrusted_annotation:
            return IntegrityLabel.UNTRUSTED
        if record.window_type == WindowType.SYSTEM and record.uid in self.system_uids:
            return IntegrityLabel.SYSTEM
        if record.notification_sender is not None:
            if record.notification_sender in self.system_packages:
                return IntegrityLabel.SYSTEM
            return IntegrityLabel.NOTIFICATION
        if record.window_type == WindowType.SDK_SURFACE:
            return IntegrityLabel.SDK
        if record.web_origin is not None:
            return IntegrityLabel.WEB
        if record.window_type == WindowType.OVERLAY and record.uid != self.target_app_uid:
            return IntegrityLabel.UNTRUSTED
        if record.window_type == WindowType.APPLICATION:
            return IntegrityLabel.APP
        return IntegrityLabel.UNTRUSTED

    def apply(self, region: Region) -> Region:
        return replace(
            region,
            label=self.label(
                region.provenance,
                user_input=bool(region.metadata.get("user_input", False)),
                developer_untrusted_annotation=bool(
                    region.metadata.get("developer_untrusted_annotation", False)
                ),
            ),
        )


def tile_label(contributing_labels: Iterable[IntegrityLabel]) -> IntegrityLabel:
    """Paper Eq. (2): join the labels of non-transparent contributing layers."""

    return join_all(contributing_labels)

