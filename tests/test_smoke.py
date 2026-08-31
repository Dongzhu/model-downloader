# minimal smoke test to ensure pytest runs at least one test

def test_imports():
    import download_core
    import download_worker
    assert True
