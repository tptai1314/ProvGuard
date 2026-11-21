def test_public_imports() -> None:
    import provguard

    assert provguard.__version__ == "0.1.0"
    assert provguard.CausalGate is not None

