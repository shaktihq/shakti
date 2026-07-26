"""The ``shakti`` command-line interface.

Phase 1: new, run, version
Phase 2: generate model|crud|api, makemigrations, migrate, db history, db current
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from shakti.__about__ import __version__
from shakti.cli import templates

PROJECT_NAME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")


# ---------------------------------------------------------------------------
# Phase 1 commands
# ---------------------------------------------------------------------------

def _scaffold_files(project: str) -> dict[str, str]:
    substitute = {"project": project}
    return {
        "app/__init__.py": templates.APP_INIT.substitute(substitute),
        "app/main.py": templates.APP_MAIN.substitute(substitute),
        "app/models/__init__.py": templates.MODELS_INIT.substitute(substitute),
        "config/settings.yaml": templates.SETTINGS_YAML.substitute(substitute),
        "config/settings.production.yaml": templates.SETTINGS_PRODUCTION_YAML.substitute(substitute),
        "tests/test_app.py": templates.TEST_APP.substitute(substitute),
        "conftest.py": templates.CONFTEST.substitute(substitute),
        ".env": templates.ENV_FILE.substitute(substitute),
        ".gitignore": templates.GITIGNORE.substitute(substitute),
        "README.md": templates.PROJECT_README.substitute(substitute),
        "requirements.txt": templates.REQUIREMENTS.substitute(substitute),
    }


def cmd_new(args: argparse.Namespace) -> int:
    name: str = args.name
    if not PROJECT_NAME_PATTERN.match(name):
        print(
            f"error: invalid project name {name!r} "
            "(use letters, digits, '-' and '_'; must start with a letter)",
            file=sys.stderr,
        )
        return 1
    root = Path(args.directory) / name
    if root.exists():
        print(f"error: {root} already exists", file=sys.stderr)
        return 1

    for relative_path, content in _scaffold_files(name).items():
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    print(f"✔ Created project {name!r} at {root}")
    print()
    print("Next steps:")
    print(f"  cd {name}")
    print("  pip install -r requirements.txt")
    print("  shakti run --reload")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path.cwd()))
    try:
        import uvicorn
    except ImportError:
        print(
            "error: uvicorn is required to run the server.\n"
            "Install it with: pip install 'shakti-framework[server]'",
            file=sys.stderr,
        )
        return 1

    kwargs: dict[str, object] = {
        "host": args.host,
        "port": args.port,
        "reload": args.reload,
    }
    if not args.reload and args.workers:
        kwargs["workers"] = args.workers
    uvicorn.run(args.app, **kwargs)
    return 0


def cmd_version(args: argparse.Namespace) -> int:
    print(f"shakti {__version__}")
    return 0


# ---------------------------------------------------------------------------
# Phase 2: generate
# ---------------------------------------------------------------------------

def cmd_generate(args: argparse.Namespace) -> int:
    from shakti.cli.codegen import write_crud, write_model

    project_dir = Path.cwd()
    kind: str = args.kind
    name: str = args.name
    fields: list[str] = args.fields or []

    # Validate model name
    if not re.match(r"^[A-Z][a-zA-Z0-9]+$", name):
        print(
            f"error: model name must be PascalCase, got {name!r}",
            file=sys.stderr,
        )
        return 1

    try:
        if kind == "model":
            files = write_model(project_dir, name, fields)
            for f in files:
                print(f"✔ {f.relative_to(project_dir)}")
            print(f"\nNext: shakti makemigrations 'add {name.lower()}'")

        elif kind == "crud":
            files = write_crud(project_dir, name)
            for f in files:
                print(f"✔ {f.relative_to(project_dir)}")
            print("\nMount in app/main.py:")
            snake = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
            print(f"  from app.routers.{snake} import router as {snake}_router")
            print(f"  app.include_router({snake}_router)")

        elif kind == "api":
            if not fields:
                print("error: 'generate api' requires at least one field", file=sys.stderr)
                return 1
            model_files = write_model(project_dir, name, fields)
            crud_files = write_crud(project_dir, name)
            for f in [*model_files, *crud_files]:
                print(f"✔ {f.relative_to(project_dir)}")
            snake = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
            print("\nMount router and run migrations:")
            print(f"  from app.routers.{snake} import router as {snake}_router")
            print(f"  app.include_router({snake}_router)")
            print(f"  shakti makemigrations 'add {snake}'")
            print("  shakti migrate")
        else:
            print(f"error: unknown generate target {kind!r}. Use: model | crud | api", file=sys.stderr)
            return 1

    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


# ---------------------------------------------------------------------------
# Phase 2: migrations
# ---------------------------------------------------------------------------

def cmd_makemigrations(args: argparse.Namespace) -> int:
    from shakti.orm.migrations import make_migrations
    return make_migrations(Path.cwd(), args.message)


def cmd_migrate(args: argparse.Namespace) -> int:
    from shakti.orm.migrations import migrate
    return migrate(Path.cwd(), args.revision)


def cmd_db(args: argparse.Namespace) -> int:
    from shakti.orm.migrations import migration_current, migration_history
    if args.subcommand == "history":
        return migration_history(Path.cwd())
    if args.subcommand == "current":
        return migration_current(Path.cwd())
    print(f"error: unknown db subcommand {args.subcommand!r}", file=sys.stderr)
    return 1


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shakti",
        description="Shakti — an AI-first, async Python web framework.",
    )
    subparsers = parser.add_subparsers(dest="command")

    # --- new ---
    new_p = subparsers.add_parser("new", help="Scaffold a new Shakti project")
    new_p.add_argument("name", help="Project name")
    new_p.add_argument("--directory", default=".", help="Parent directory (default: .)")
    new_p.set_defaults(handler=cmd_new)

    # --- run ---
    run_p = subparsers.add_parser("run", help="Start the dev server (uvicorn)")
    run_p.add_argument("app", nargs="?", default="app.main:app",
                       help="Import string (default: app.main:app)")
    run_p.add_argument("--host", default="127.0.0.1")
    run_p.add_argument("--port", type=int, default=8000)
    run_p.add_argument("--reload", action="store_true")
    run_p.add_argument("--workers", type=int, default=None)
    run_p.set_defaults(handler=cmd_run)

    # --- version ---
    ver_p = subparsers.add_parser("version", help="Print installed version")
    ver_p.set_defaults(handler=cmd_version)

    # --- generate ---
    gen_p = subparsers.add_parser("generate", aliases=["g"],
                                  help="Generate model, crud, or api scaffold")
    gen_p.add_argument("kind", choices=["model", "crud", "api"],
                       help="What to generate")
    gen_p.add_argument("name", help="Model name in PascalCase (e.g. BlogPost)")
    gen_p.add_argument("fields", nargs="*",
                       help="Field specs: name:type[:modifier] — e.g. title:str body:text views:int")
    gen_p.set_defaults(handler=cmd_generate)

    # --- makemigrations ---
    mm_p = subparsers.add_parser("makemigrations", aliases=["mm"],
                                 help="Auto-generate a migration from model changes")
    mm_p.add_argument("message", nargs="?", default="auto",
                      help="Migration message (default: auto)")
    mm_p.set_defaults(handler=cmd_makemigrations)

    # --- migrate ---
    mig_p = subparsers.add_parser("migrate", help="Apply pending migrations")
    mig_p.add_argument("revision", nargs="?", default="head",
                       help="Target revision (default: head)")
    mig_p.set_defaults(handler=cmd_migrate)

    # --- db ---
    db_p = subparsers.add_parser("db", help="Database utilities")
    db_sub = db_p.add_subparsers(dest="subcommand")
    db_sub.add_parser("history", help="Show migration history")
    db_sub.add_parser("current", help="Show current migration")
    db_p.set_defaults(handler=cmd_db)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "handler", None) is None:
        parser.print_help()
        return 1
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
