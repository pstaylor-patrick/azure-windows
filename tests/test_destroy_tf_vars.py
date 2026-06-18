def test_destroy_tf_vars_with_creds(awvm):
    creds = awvm.Credentials(
        run_id="abcd",
        region="eastus2",
        rg_name="rg",
        vm_name="vm",
        nsg_name="nsg",
        public_ip="1.2.3.4",
        username="azureuser",
        password="P@ss1",
        allowed_cidr="1.2.3.4/32",
        created_at="2024-01-01T00:00:00",
        size="Standard_D2s_v3",
    )
    tf_vars = awvm._destroy_tf_vars(creds, None)
    assert tf_vars["vm_admin_password"] == "P@ss1"
    assert tf_vars["vm_run_id"] == "abcd"
