import importlib.util
import pathlib
import sys
import pytest


@pytest.fixture(scope="session")
def awvm():
    spec = importlib.util.spec_from_file_location(
        "awvm", pathlib.Path(__file__).resolve().parent.parent / "scripts" / "awvm.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["awvm"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def tmp_state(awvm, tmp_path, monkeypatch):
    monkeypatch.setattr(awvm, "STATE_DIR", tmp_path)
    monkeypatch.setattr(awvm, "CRED_FILE", tmp_path / "credentials.json")
    monkeypatch.setattr(awvm, "RUN_POINTER", tmp_path / "current_run")
    monkeypatch.setattr(awvm, "RDP_FILE", tmp_path / "vm.rdp")
    return tmp_path
