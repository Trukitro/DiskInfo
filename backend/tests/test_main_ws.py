import sys

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="starts the full app, including the WMI-backed poll loop"
)


@pytest.fixture(autouse=True)
def _fast_quiet_poll_loop(monkeypatch):
    """Every test in this module starts the real app (lifespan runs the
    real poll loop against real WMI). Two real-settings side effects would
    otherwise leak into a test run: a 5s wait for the first broadcast, and
    genuine Windows toast notifications firing if a real drive on the test
    machine happens to be over the real low_space_pct threshold."""
    monkeypatch.setattr(main_module.settings, "poll_interval_s", 0.2)
    monkeypatch.setattr(main_module.settings, "notifications_enabled", False)


def test_websocket_receives_a_tick_message():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            message = ws.receive_json()
            assert message["type"] == "tick"
            assert "drives" in message["data"]
            assert "health" in message["data"]
            assert "io_activity" in message["data"]


def test_websocket_reconnect_after_disconnect_still_works():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as first:
            first.receive_json()
        # Exercises ConnectionManager.disconnect() actually clearing the
        # closed socket out of its set -- a second connection afterward
        # should behave identically, not silently broadcast into a stale
        # reference from the first one.
        with client.websocket_connect("/ws") as second:
            message = second.receive_json()
            assert message["type"] == "tick"


def test_two_concurrent_connections_both_receive_ticks():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as first, client.websocket_connect("/ws") as second:
            msg1 = first.receive_json()
            msg2 = second.receive_json()
            assert msg1["type"] == "tick"
            assert msg2["type"] == "tick"
