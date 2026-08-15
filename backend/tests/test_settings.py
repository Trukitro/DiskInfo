from app.settings import Settings, load_settings, save_settings


def test_load_settings_returns_defaults_when_file_missing(settings_path):
    assert load_settings(settings_path) == Settings()


def test_save_then_load_roundtrips(settings_path):
    original = Settings(poll_interval_s=10.0, low_space_pct=80.0, autostart=True, last_selected_drive="D")
    save_settings(original, settings_path)
    assert load_settings(settings_path) == original


def test_load_settings_ignores_unknown_keys(settings_path):
    settings_path.write_text('{"poll_interval_s": 3.0, "made_up_field": "x"}', encoding="utf-8")
    assert load_settings(settings_path).poll_interval_s == 3.0


def test_load_settings_falls_back_to_defaults_on_corrupt_json(settings_path):
    settings_path.write_text("not json", encoding="utf-8")
    assert load_settings(settings_path) == Settings()


def test_temperature_alert_c_defaults_to_none_and_roundtrips(settings_path):
    assert Settings().temperature_alert_c is None
    original = Settings(temperature_alert_c=55)
    save_settings(original, settings_path)
    assert load_settings(settings_path).temperature_alert_c == 55
