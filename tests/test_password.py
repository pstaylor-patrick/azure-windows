import re


def test_password_length(awvm):
    for _ in range(100):
        pw = awvm._generate_password()
        assert len(pw) == 24
        assert re.search(r"[A-Z]", pw)
        assert re.search(r"[a-z]", pw)
        assert re.search(r"[0-9]", pw)
        assert re.search(r"[^A-Za-z0-9]", pw)
