def test_rdp_crlf(awvm, tmp_state):
    awvm._write_rdp_file("1.2.3.4", "azureuser")
    content = awvm.RDP_FILE.read_bytes()
    assert b"\r\n" in content
    assert b"full address:s:1.2.3.4" in content
