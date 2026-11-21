import pytest

from provguard.metrics import (
    attack_success_rate,
    false_block_rate,
    latency_summary,
    precision_recall,
    task_success_rate,
)


def test_paper_metric_formulas() -> None:
    records = [
        {"trial_type": "attack", "channel": "ad", "adversarial_success": True},
        {"trial_type": "attack", "channel": "ad", "adversarial_success": False},
        {"trial_type": "benign", "protected": True, "gate_decision": "pass", "dispatch_status": "delivered", "task_completed": True},
        {"trial_type": "benign", "protected": True, "gate_decision": "escalate", "dispatch_status": "dropped", "task_completed": False},
    ]
    assert attack_success_rate(records, "ad") == 0.5
    assert false_block_rate(records) == 0.5
    assert task_success_rate(records) == 0.5
    assert precision_recall([True, False, True], [True, True, False]) == (0.5, 0.5)
    assert latency_summary([1, 2, 100])["p95_ms"] == 100
    with pytest.raises(ValueError):
        attack_success_rate(records, "missing")

