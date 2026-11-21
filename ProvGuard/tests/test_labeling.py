from provguard.labeling import DefaultLabelingPolicy, tile_label
from provguard.lattice import IntegrityLabel
from provguard.schemas import ProvenanceRecord, WindowType


def test_default_policy_and_tile_join() -> None:
    policy = DefaultLabelingPolicy(target_app_uid=42)
    web = ProvenanceRecord(42, WindowType.APPLICATION, web_origin="https://example.test")
    overlay = ProvenanceRecord(99, WindowType.OVERLAY)
    assert policy.label(web) == IntegrityLabel.WEB
    assert policy.label(overlay) == IntegrityLabel.UNTRUSTED
    assert tile_label([IntegrityLabel.WEB, IntegrityLabel.SDK]) == IntegrityLabel.UNTRUSTED

