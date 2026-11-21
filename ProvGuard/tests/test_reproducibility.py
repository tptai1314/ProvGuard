from provguard.schemas import EquivalenceMode
from provguard.synthetic import run_synthetic_trials


def test_fixed_seed_is_deterministic() -> None:
    kwargs = {
        "seed": 17,
        "repetitions": 2,
        "trials": 3,
        "threshold": 0.5,
        "equivalence": EquivalenceMode.CONTROL,
    }
    assert run_synthetic_trials(**kwargs) == run_synthetic_trials(**kwargs)
