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


def test_credentials_to_dict_no_password(awvm):
    creds = awvm.Credentials(
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
    assert "password" not in creds.to_dict()
