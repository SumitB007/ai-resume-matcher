"""Phase 8 guardrails (pure-logic): the limiter's key shapes and IP reading.

The live behaviour (429s, CORS headers, cascade) is verified against the
running stack; these pin the small pure pieces so refactors can't quietly
change what gets limited.
"""

from app.core.rate_limiter import client_ip


class _Req:
    def __init__(self, headers=None, host="192.0.2.1"):
        self.headers = headers or {}
        self.client = type("C", (), {"host": host})() if host else None


def test_client_ip_prefers_first_forwarded_hop():
    req = _Req({"x-forwarded-for": "203.0.113.7, 10.0.0.1"})
    assert client_ip(req) == "203.0.113.7"


def test_client_ip_falls_back_to_peer():
    assert client_ip(_Req()) == "192.0.2.1"
    assert client_ip(_Req(host=None)) == "unknown"
