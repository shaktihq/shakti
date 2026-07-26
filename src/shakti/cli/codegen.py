"""Code generation helpers: model, crud, api scaffolding."""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Field DSL parser
# ---------------------------------------------------------------------------
# Syntax:  fieldname:type[:length|unique|nullable|index]
# Types:   str  text  int  float  bool  datetime  uuid
#
# Examples:
#   name:str              → Mapped[str]  = Field(String(255))
#   email:str:unique      → ... unique=True
#   bio:text:nullable     → Mapped[str | None] = Field(Text, nullable=True)
#   age:int               → Mapped[int] = Field(Integer)
#   price:float           → Mapped[float] = Field(Float)
#   active:bool           → Mapped[bool] = Field(Boolean, default=True)
#   joined:datetime       → Mapped[datetime] = Field(DateTime(timezone=True))
#   token:uuid            → Mapped[str] = Field(String(36), unique=True)

_SA_IMPORTS = {
    "str":      "String",
    "text":     "Text",
    "int":      "Integer",
    "float":    "Float",
    "bool":     "Boolean",
    "datetime": "DateTime",
    "uuid":     "String",
}
_PY_TYPES = {
    "str":      "str",
    "text":     "str",
    "int":      "int",
    "float":    "float",
    "bool":     "bool",
    "datetime": "datetime",
    "uuid":     "str",
}


class FieldSpec(NamedTuple):
    name: str
    py_type: str
    sa_col: str        # full mapped_column(...) expression
    sa_import: str     # SQLAlchemy type name to import
    nullable: bool


def _parse_field(spec: str) -> FieldSpec:
    """Parse a field spec like ``email:str:unique`` into a FieldSpec."""
    parts = spec.split(":")
    name = parts[0].strip()
    raw_type = parts[1].strip() if len(parts) > 1 else "str"
    modifiers = {p.strip().lower() for p in parts[2:]}

    if raw_type not in _SA_IMPORTS:
        raise ValueError(
            f"Unknown field type {raw_type!r}. "
            f"Valid: {', '.join(_SA_IMPORTS)}"
        )

    nullable = "nullable" in modifiers
    unique = "unique" in modifiers
    index = "index" in modifiers

    sa_import = _SA_IMPORTS[raw_type]
    py_type = _PY_TYPES[raw_type]

    # Build the column expression
    if raw_type == "str":
        col_type = "String(255)"
    elif raw_type == "datetime":
        col_type = "DateTime(timezone=True)"
    elif raw_type == "uuid":
        col_type = "String(36)"
    else:
        col_type = sa_import

    opts: list[str] = []
    if unique:
        opts.append("unique=True")
    if index:
        opts.append("index=True")
    if nullable:
        opts.append("nullable=True")
    if raw_type == "bool":
        opts.append("default=False")

    opt_str = (", " + ", ".join(opts)) if opts else ""
    col_expr = f"Field({col_type}{opt_str})"
    mapped_type = f"{py_type} | None" if nullable else py_type

    return FieldSpec(name=name, py_type=mapped_type, sa_col=col_expr,
                     sa_import=sa_import, nullable=nullable)


def _to_snake(name: str) -> str:
    """UserProfile → user_profile."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _to_plural(snake: str) -> str:
    if snake.endswith("y"):
        return snake[:-1] + "ies"
    if snake.endswith(("s", "sh", "ch", "x", "z")):
        return snake + "es"
    return snake + "s"


# ---------------------------------------------------------------------------
# Model template
# ---------------------------------------------------------------------------

def generate_model(name: str, fields: list[str], *, timestamps: bool = True) -> str:
    """Return the source code for a model file."""
    parsed = [_parse_field(f) for f in fields]
    sa_types = sorted({f.sa_import for f in parsed})

    needs_datetime = any(f.sa_import == "DateTime" for f in parsed)
    datetime_import = "from datetime import datetime\n" if needs_datetime else ""

    sa_import_line = ""
    if sa_types:
        sa_import_line = f"from sqlalchemy import {', '.join(sa_types)}\n"

    ts_import = "from shakti.orm import TimestampMixin\n" if timestamps else ""
    ts_mixin = "(TimestampMixin, Base)" if timestamps else "(Base)"

    field_lines = ""
    for f in parsed:
        field_lines += f"    {f.name}: Mapped[{f.py_type}] = {f.sa_col}\n"

    snake = _to_snake(name)
    table = _to_plural(snake)

    return (
        f'"""Model: {name}"""\n\n'
        f"from __future__ import annotations\n\n"
        f"{datetime_import}"
        f"from sqlalchemy.orm import Mapped\n"
        f"{sa_import_line}"
        f"from shakti.orm import Base, Field\n"
        f"{ts_import}\n\n"
        f"class {name}{ts_mixin}:\n"
        f'    __tablename__ = "{table}"\n\n'
        f"{field_lines}"
        f"\n    def __repr__(self) -> str:\n"
        f'        return f"<{name} id={{self.id}}>"\n'
    )


# ---------------------------------------------------------------------------
# CRUD router template
# ---------------------------------------------------------------------------

def generate_crud(name: str) -> str:
    """Return a full CRUD router for *name*."""
    snake = _to_snake(name)
    plural = _to_plural(snake)
    lower = snake

    return f'''"""CRUD endpoints for {name}."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from shakti import Depends, HTTPException, Router
from shakti.orm import Database, Repository
from app.models.{lower} import {name}

router = Router(prefix="/{plural}")


def _repo(session: AsyncSession = Depends(Database.get_session)) -> Repository[{name}]:
    return Repository({name}, session)


@router.get("/")
async def list_{plural}(repo: Repository = Depends(_repo)) -> list[dict]:
    items = await repo.all()
    return [i.to_dict() for i in items]


@router.get("/{{id:int}}")
async def get_{lower}(id: int, repo: Repository = Depends(_repo)) -> dict:
    return (await repo.get_or_404(id)).to_dict()


@router.post("/")
async def create_{lower}(body: dict, repo: Repository = Depends(_repo)) -> dict:
    obj = await repo.create(**body)
    return obj.to_dict()


@router.put("/{{id:int}}")
async def update_{lower}(id: int, body: dict, repo: Repository = Depends(_repo)) -> dict:
    obj = await repo.get_or_404(id)
    return (await repo.update(obj, **body)).to_dict()


@router.delete("/{{id:int}}")
async def delete_{lower}(id: int, repo: Repository = Depends(_repo)) -> dict:
    obj = await repo.get_or_404(id)
    await repo.delete(obj)
    return {{"deleted": id}}
'''


# ---------------------------------------------------------------------------
# Full API template (model + crud in one shot)
# ---------------------------------------------------------------------------

def generate_api(name: str, fields: list[str]) -> tuple[str, str]:
    """Return (model_source, crud_source) for a complete API resource."""
    return generate_model(name, fields), generate_crud(name)


# ---------------------------------------------------------------------------
# Writer helper
# ---------------------------------------------------------------------------

def write_model(project_dir: Path, name: str, fields: list[str]) -> list[Path]:
    snake = _to_snake(name)
    models_dir = project_dir / "app" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    model_file = models_dir / f"{snake}.py"
    model_file.write_text(generate_model(name, fields), encoding="utf-8")

    # Create/update __init__.py to import the model (so Alembic picks it up)
    init_file = models_dir / "__init__.py"
    init_text = init_file.read_text(encoding="utf-8") if init_file.is_file() else ""
    import_line = f"from app.models.{snake} import {name}  # noqa: F401\n"
    if import_line not in init_text:
        init_file.write_text(init_text + import_line, encoding="utf-8")

    return [model_file, init_file]


def write_crud(project_dir: Path, name: str) -> list[Path]:
    snake = _to_snake(name)
    routers_dir = project_dir / "app" / "routers"
    routers_dir.mkdir(parents=True, exist_ok=True)

    crud_file = routers_dir / f"{snake}.py"
    crud_file.write_text(generate_crud(name), encoding="utf-8")

    init_file = routers_dir / "__init__.py"
    if not init_file.is_file():
        init_file.write_text("", encoding="utf-8")

    return [crud_file, init_file]
