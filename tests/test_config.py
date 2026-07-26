import pytest

from shakti.config import Config, Secret
from shakti.exceptions import ConfigError


@pytest.fixture()
def config_env(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.yaml").write_text(
        "app:\n"
        "  name: demo\n"
        "  debug: true\n"
        "database:\n"
        "  url: sqlite:///dev.db\n"
        "  pool: 5\n",
        encoding="utf-8",
    )
    (config_dir / "settings.production.yaml").write_text(
        "app:\n"
        "  debug: false\n"
        "database:\n"
        "  url: ${DATABASE_URL:postgresql://prod-default}\n",
        encoding="utf-8",
    )
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# local overrides\n"
        "API_TOKEN=abc123\n"
        "export EXTRA='quoted value'\n"
        "PORT=8080 # inline comment\n",
        encoding="utf-8",
    )
    return config_dir, env_file


def make(config_env, profile="development"):
    config_dir, env_file = config_env
    return Config(config_dir, env_file=env_file, profile=profile)


def test_yaml_base_values(config_env) -> None:
    config = make(config_env)
    assert config.get("app.name") == "demo"
    assert config.get("app.debug") is True
    assert config.get("database.pool") == 5


def test_profile_overrides(config_env) -> None:
    config = make(config_env, profile="production")
    assert config.get("app.debug") is False
    assert config.get("app.name") == "demo"  # inherited from base


def test_env_var_overrides_yaml(config_env, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE__URL", "mysql://override")
    config = make(config_env)
    assert config.get("database.url") == "mysql://override"


def test_env_file_values(config_env) -> None:
    config = make(config_env)
    assert config.get("api_token") == "abc123"
    assert config.get("extra") == "quoted value"
    assert config.get("port", cast=int) == 8080


def test_yaml_interpolation_with_default(config_env, monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    config = make(config_env, profile="production")
    assert config.get("database.url") == "postgresql://prod-default"
    monkeypatch.setenv("DATABASE_URL", "postgresql://real")
    assert config.get("database.url") == "postgresql://real"


def test_require_missing_raises(config_env) -> None:
    config = make(config_env)
    with pytest.raises(ConfigError):
        config.require("does.not.exist")


def test_bool_cast_from_env(config_env, monkeypatch) -> None:
    monkeypatch.setenv("FEATURE_FLAG", "yes")
    config = make(config_env)
    assert config.get("feature_flag", cast=bool) is True


def test_secret_from_file(config_env, tmp_path, monkeypatch) -> None:
    secret_file = tmp_path / "db_password.txt"
    secret_file.write_text("s3cr3t\n", encoding="utf-8")
    monkeypatch.setenv("DB_PASSWORD_FILE", str(secret_file))
    config = make(config_env)
    secret = config.secret("db_password")
    assert isinstance(secret, Secret)
    assert secret.get_secret_value() == "s3cr3t"
    assert "s3cr3t" not in repr(secret)
    assert str(secret) == "**********"


def test_secret_missing_returns_none(config_env) -> None:
    config = make(config_env)
    assert config.secret("missing_secret") is None
