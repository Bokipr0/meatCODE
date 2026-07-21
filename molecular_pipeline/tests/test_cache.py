import time

from moldedup.cache import HttpCache


def test_set_get_roundtrip(tmp_path):
    c = HttpCache(str(tmp_path / "c.sqlite"))
    assert c.get("k") is None
    c.set("k", 200, '{"a":1}')
    got = c.get("k")
    assert got == {"status": 200, "body": '{"a":1}'}


def test_negative_result_is_cached(tmp_path):
    c = HttpCache(str(tmp_path / "c.sqlite"))
    c.set("missing", 404, "")
    assert c.get("missing") == {"status": 404, "body": ""}


def test_ttl_expiry(tmp_path):
    c = HttpCache(str(tmp_path / "c.sqlite"), ttl=0.05)
    c.set("k", 200, "x")
    assert c.get("k") is not None
    time.sleep(0.08)
    assert c.get("k") is None
