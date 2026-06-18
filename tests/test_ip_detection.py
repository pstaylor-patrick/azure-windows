from unittest.mock import MagicMock


def test_valid_ip(awvm, monkeypatch):
    mock_resp = MagicMock()
    mock_resp.text = "1.2.3.4"
    monkeypatch.setattr(awvm.requests, "get", lambda *a, **kw: mock_resp)
    assert awvm._detect_public_ip() == "1.2.3.4"


def test_malformed_ip_falls_through(awvm, monkeypatch):
    call_count = {"n": 0}

    def fake_get(url, **kw):
        r = MagicMock()
        r.text = "not-an-ip" if call_count["n"] == 0 else "5.6.7.8"
        call_count["n"] += 1
        return r

    monkeypatch.setattr(awvm.requests, "get", fake_get)
    assert awvm._detect_public_ip() == "5.6.7.8"
