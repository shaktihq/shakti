# Configuration

`Config` layers settings from several sources, highest priority first:

1. `os.environ` — dotted keys map to `UPPER__CASE` (`db.url` → `DB__URL`)
2. a `.env` file (defaults to `.env` in the working directory)
3. `config/settings.<profile>.yaml`
4. `config/settings.yaml`
5. constructor `defaults`

```python
from shakti import Config

config = Config()  # profile from SHAKTI_ENV, defaults to "development"
app = Shakti(config=config)
```

## Reading values

```python
config.get("app.debug", default=False, cast=bool)
config.require("db.url")            # raises ConfigError if missing
config.get("server.port", 8000, cast=int)
```

`get()` returns `default` if the key isn't found anywhere. `require()` raises `ConfigError` instead. `cast` accepts any callable; passing `bool` uses a lenient truthy/falsy parser (`"1"/"true"/"yes"/"on"` → `True`, `"0"/"false"/"no"/"off"` → `False`) rather than Python's own `bool()`.

Keys are dotted paths into the merged YAML tree:

```yaml
# config/settings.yaml
app:
  debug: false
db:
  url: "sqlite+aiosqlite:///./app.db"
```

```python
config.get("app.debug")   # False
config.get("db.url")      # "sqlite+aiosqlite:///./app.db"
```

## Environment variable interpolation

String values in YAML support `${ENV_VAR}` and `${ENV_VAR:default}`:

```yaml
db:
  url: "${DATABASE_URL:sqlite+aiosqlite:///./app.db}"
ai:
  api_key: "${ANTHROPIC_API_KEY}"
```

## Profiles

`Config(profile="production")` (or the `SHAKTI_ENV` environment variable) selects `config/settings.production.yaml`, which is deep-merged on top of the base `config/settings.yaml` — set shared defaults in the base file and override per-environment values in the profile file.

## Secrets

`config.secret(key)` returns a `Secret` wrapper (its `repr()` never shows the value, so it's safe to log a config object without leaking it):

```python
api_key = config.secret("ai.api_key")
api_key.get_secret_value()
```

It also supports Docker/Kubernetes-style file-based secrets: if `<KEY>_FILE` is set (e.g. `DB__PASSWORD_FILE=/run/secrets/db_password`), the value is read from that file instead of the environment directly.

## Environment variable naming

Dotted keys map to environment variables by uppercasing and replacing `.`/`-` with `_`: `db.url` → `DB__URL`, `app.debug` → `APP__DEBUG`. Environment variables always win over YAML and defaults.
