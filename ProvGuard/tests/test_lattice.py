import itertools

from provguard.lattice import IntegrityLabel, join, leq, meet


def test_paper_lattice_incomparable_channels() -> None:
    assert not leq(IntegrityLabel.WEB, IntegrityLabel.SDK)
    assert join(IntegrityLabel.WEB, IntegrityLabel.SDK) == IntegrityLabel.UNTRUSTED
    assert meet(IntegrityLabel.WEB, IntegrityLabel.SDK) == IntegrityLabel.APP


def test_join_and_meet_are_commutative() -> None:
    for left, right in itertools.product(IntegrityLabel, repeat=2):
        assert join(left, right) == join(right, left)
        assert meet(left, right) == meet(right, left)

