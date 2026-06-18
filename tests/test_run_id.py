import re


def test_run_id_format(awvm):
    for _ in range(50):
        rid = awvm._generate_run_id()
        assert re.match(r"^[a-z0-9]{4}$", rid)
