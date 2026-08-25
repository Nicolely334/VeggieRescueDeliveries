from app.core.config import Settings


def test_settings_have_development_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_name == "Veggie Rescue Deliveries API"
    assert settings.app_environment == "development"
    assert settings.debug is False


def test_settings_read_environment_variables(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENVIRONMENT", "test")
    monkeypatch.setenv("DEBUG", "true")

    settings = Settings(_env_file=None)

    assert settings.app_environment == "test"
    assert settings.debug is True
