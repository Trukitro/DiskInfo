"""Shared fixtures. tmp_path already gives each test an isolated directory;
these just name the settings/history files within it so tests never touch
the developer's real %LOCALAPPDATA%\\DiskInfo."""

import pytest


@pytest.fixture
def settings_path(tmp_path):
    return tmp_path / "settings.json"


@pytest.fixture
def history_path(tmp_path):
    return tmp_path / "history.db"
