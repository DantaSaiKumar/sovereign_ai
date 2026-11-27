from sovereign.audit import append_event, verify_chain

def test_audit_chain_verifies():
    append_event("unit_test", {"value": 7})
    append_event("second_event", {"status": "ok"})
    valid, count = verify_chain()
    assert valid and count == 2
