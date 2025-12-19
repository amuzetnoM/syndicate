from scripts.notion_webhooks import extract_data_source_id, normalize_event


def test_extract_data_source_id_present():
    evt = {"data": {"parent": {"type": "database", "data_source_id": "ds-1"}}}
    assert extract_data_source_id(evt) == "ds-1"


def test_extract_data_source_id_missing():
    evt = {"data": {"parent": {"type": "database"}}}
    assert extract_data_source_id(evt) is None


def test_normalize_event():
    evt = {"type": "page.created", "data": {"parent": {"data_source_id": "ds-1"}}}
    n = normalize_event(evt)
    assert n["type"] == "page.created"
    assert n["data_source_id"] == "ds-1"