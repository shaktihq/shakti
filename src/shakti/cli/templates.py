"""File templates used by ``shakti new``."""

from __future__ import annotations

from string import Template

APP_MAIN = Template('''"""$project — built with Shakti."""

from shakti import Shakti, Router
from shakti.config import Config

config = Config()
app = Shakti(title="$project", config=config)

api = Router(prefix="/api")


@app.get("/")
async def index() -> dict:
    return {"app": "$project", "status": "running"}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@api.get("/hello/{name}")
async def hello(name: str) -> dict:
    return {"message": f"Hello, {name}!"}


app.include_router(api)
''')

APP_INIT = Template('"""$project application package."""\n')

MODELS_INIT = Template('"""$project models — imported here so Alembic sees all metadata."""\n')

SETTINGS_YAML = Template('''app:
  name: $project
  debug: true

server:
  host: 127.0.0.1
  port: 8000

database:
  url: sqlite+aiosqlite:///./$project.db
''')

SETTINGS_PRODUCTION_YAML = Template('''app:
  debug: false

database:
  url: $${DATABASE_URL}
''')

ENV_FILE = Template('''# Environment profile: development | production | any custom name
SHAKTI_ENV=development

# Database URL (overrides config/settings.yaml)
# DATABASE__URL=postgresql+asyncpg://user:pass@localhost/$project

# Secrets
# SECRET_KEY=change-me
''')

CONFTEST = Template('''"""Ensures the project root is importable when running pytest."""
''')

TEST_APP = Template('''from shakti.testing import TestClient

from app.main import app

client = TestClient(app)


def test_index() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["app"] == "$project"


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_hello() -> None:
    response = client.get("/api/hello/forge")
    assert response.json() == {"message": "Hello, forge!"}
''')

PROJECT_README = Template('''# $project

Built with [Shakti](https://github.com/shakti/shakti).

## Run

```bash
pip install -r requirements.txt
shakti run --reload
```

## Generate a model

```bash
shakti generate model Post title:str body:text published:bool
shakti generate crud Post
shakti makemigrations "add posts"
shakti migrate
```

## Test

```bash
pytest
```
''')

REQUIREMENTS = Template('''shakti-framework[server]>=0.1.0
sqlalchemy[asyncio]>=2.0
alembic>=1.13
aiosqlite>=0.20
pytest>=8.0
pytest-asyncio>=0.23
''')

GITIGNORE = Template('''__pycache__/
*.py[cod]
.venv/
.env
.pytest_cache/
*.sqlite3
*.db
migrations/versions/
''')
