import pytest


@pytest.fixture
def fake_keyring(awvm, monkeypatch):
    store = {}

    class FakeKeyring:
        def get_password(self, service, account):
            return store.get((service, account))

        def set_password(self, service, account, password):
            store[(service, account)] = password

        def delete_password(self, service, account):
            if (service, account) not in store:
                import keyring.errors

                raise keyring.errors.PasswordDeleteError("not found")
            del store[(service, account)]

    import keyring as kr

    fk = FakeKeyring()
    monkeypatch.setattr(kr, "get_password", fk.get_password)
    monkeypatch.setattr(kr, "set_password", fk.set_password)
    monkeypatch.setattr(kr, "delete_password", fk.delete_password)
    monkeypatch.setattr(awvm, "keyring", kr)
    return store


def test_store_load_delete(awvm, fake_keyring):
    awvm._store_password("run1", "secret")
    assert awvm._load_password("run1") == "secret"
    awvm._delete_password("run1")
    assert awvm._load_password("run1") is None


CRED_FIELDS = dict(
    run_id="abcd",
    region="eastus2",
    rg_name="rg",
    vm_name="vm",
    nsg_name="nsg",
    public_ip="1.2.3.4",
    username="azureuser",
    password="secret",
    allowed_cidr="1.2.3.4/32",
    created_at="2024-01-01T00:00:00",
    size="Standard_D2s_v3",
)


def test_credentials_to_dict_no_password(awvm):
    creds = awvm.Credentials(**CRED_FIELDS)
    d = creds.to_dict()
    assert "password" not in d
    # all other fields survive the round-trip
    for key, val in CRED_FIELDS.items():
        if key != "password":
            assert d[key] == val, f"field {key!r} missing or wrong in to_dict()"


def test_read_credentials_migration_shim(awvm, tmp_state, fake_keyring):
    """Old-format credentials.json (password in JSON) is migrated to Keychain on read."""
    import json

    old_data = {**CRED_FIELDS}  # includes password
    (tmp_state / "credentials.json").write_text(json.dumps(old_data))

    creds = awvm._read_credentials()

    # Password is returned on the object
    assert creds is not None
    assert creds.password == "secret"

    # Password is now in the fake Keychain
    assert fake_keyring[("awvm", "abcd")] == "secret"

    # credentials.json no longer contains the password
    on_disk = json.loads((tmp_state / "credentials.json").read_text())
    assert "password" not in on_disk


def test_read_credentials_new_format(awvm, tmp_state, fake_keyring):
    """New-format credentials.json (no password field) hydrates from Keychain."""
    import json

    new_data = {k: v for k, v in CRED_FIELDS.items() if k != "password"}
    (tmp_state / "credentials.json").write_text(json.dumps(new_data))
    fake_keyring[("awvm", "abcd")] = "secret"

    creds = awvm._read_credentials()

    assert creds is not None
    assert creds.password == "secret"
    # File should be unchanged (no rewrite triggered)
    on_disk = json.loads((tmp_state / "credentials.json").read_text())
    assert "password" not in on_disk
