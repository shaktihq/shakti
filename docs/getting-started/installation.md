# Installation

Shakti requires **Python 3.12+**.

## Install

```bash
pip install "shakti-framework[server]"
```

## Optional extras

```bash
pip install "shakti-framework[orm]"        # SQLAlchemy + Alembic
pip install "shakti-framework[auth]"       # JWT + bcrypt
pip install "shakti-framework[ai]"         # Claude + OpenAI
pip install "shakti-framework[docs]"       # PDF + OCR
pip install "shakti-framework[monitoring]" # psutil metrics
pip install "shakti-framework[all]"        # everything
```

## Verify

```bash
shakti version
# shakti 0.1.0
```
