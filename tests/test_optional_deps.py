"""Regression test: `import shakti` must work with only the base dependency
(pyyaml) installed — sqlalchemy/bcrypt/PyJWT (the orm/auth extras) must not
be required just to import the package. See shakti/__init__.py's lazy
Admin/Auth/APIKey/User loading.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

SRC_DIR = str(Path(__file__).resolve().parent.parent / "src")


def test_import_shakti_without_orm_or_auth_extras() -> None:
    script = textwrap.dedent(
        """
        import sys
        for mod in (
            "sqlalchemy", "bcrypt", "jwt", "alembic", "aiosqlite",
            "anthropic", "openai", "psutil", "redis", "pypdf", "PIL",
        ):
            sys.modules[mod] = None

        import shakti
        assert shakti.Shakti
        assert shakti.Router
        assert shakti.HTTPException
        assert shakti.StaticFiles
        assert shakti.SecurityHeadersMiddleware
        assert shakti.WorkflowEngine
        print("OK")
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        check=False,
        text=True,
        cwd=SRC_DIR,
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_accessing_admin_without_sqlalchemy_raises_import_error() -> None:
    script = textwrap.dedent(
        """
        import sys
        sys.modules["sqlalchemy"] = None
        import shakti
        try:
            shakti.Admin
        except ImportError:
            print("RAISED")
        else:
            print("DID NOT RAISE")
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        check=False,
        text=True,
        cwd=SRC_DIR,
    )
    assert result.returncode == 0, result.stderr
    assert "RAISED" in result.stdout
