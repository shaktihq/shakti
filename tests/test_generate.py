"""Phase 2: Code generation tests."""

from __future__ import annotations

from pathlib import Path

from shakti.cli.codegen import generate_crud, generate_model, write_crud, write_model
from shakti.cli.main import main


def test_generate_model_basic():
    src = generate_model("Post", ["title:str", "views:int", "active:bool"])
    assert "class Post" in src
    assert "__tablename__ = \"posts\"" in src
    assert "Mapped[str]" in src
    assert "Mapped[int]" in src
    assert "Field(String(255))" in src


def test_generate_model_nullable():
    src = generate_model("Tag", ["name:str", "desc:text:nullable"])
    assert "str | None" in src
    assert "nullable=True" in src


def test_generate_model_unique():
    src = generate_model("User", ["email:str:unique"])
    assert "unique=True" in src


def test_generate_model_with_timestamps():
    src = generate_model("Event", ["name:str"], timestamps=True)
    assert "TimestampMixin" in src


def test_generate_model_no_timestamps():
    src = generate_model("Event", ["name:str"], timestamps=False)
    assert "TimestampMixin" not in src


def test_generate_model_invalid_type():
    import pytest
    with pytest.raises(ValueError, match="Unknown field type"):
        generate_model("X", ["name:badtype"])


def test_generate_crud_basic():
    src = generate_crud("Post")
    assert "Router(prefix=\"/posts\")" in src
    assert "async def list_posts" in src
    assert "async def get_post" in src
    assert "async def create_post" in src
    assert "async def update_post" in src
    assert "async def delete_post" in src


def test_generate_crud_pascal_to_snake():
    src = generate_crud("BlogPost")
    assert '"/blog_posts"' in src
    assert "list_blog_posts" in src


def test_write_model_creates_files(tmp_path):
    files = write_model(tmp_path, "Article", ["headline:str", "content:text"])
    assert (tmp_path / "app/models/article.py").is_file()
    assert (tmp_path / "app/models/__init__.py").is_file()
    init = (tmp_path / "app/models/__init__.py").read_text()
    assert "from app.models.article import Article" in init


def test_write_model_idempotent_init(tmp_path):
    write_model(tmp_path, "Article", ["headline:str"])
    write_model(tmp_path, "Article", ["headline:str"])  # second write
    init = (tmp_path / "app/models/__init__.py").read_text()
    assert init.count("from app.models.article import Article") == 1


def test_write_crud_creates_files(tmp_path):
    write_model(tmp_path, "Article", ["headline:str"])
    write_crud(tmp_path, "Article")
    assert (tmp_path / "app/routers/article.py").is_file()


def test_cli_generate_model(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    result = main(["generate", "model", "Product", "name:str", "price:float", "stock:int"])
    assert result == 0
    assert (tmp_path / "app/models/product.py").is_file()


def test_cli_generate_crud(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    write_model(tmp_path, "Product", ["name:str"])
    result = main(["generate", "crud", "Product"])
    assert result == 0
    assert (tmp_path / "app/routers/product.py").is_file()


def test_cli_generate_api(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    result = main(["generate", "api", "Category", "name:str", "slug:str:unique"])
    assert result == 0
    assert (tmp_path / "app/models/category.py").is_file()
    assert (tmp_path / "app/routers/category.py").is_file()


def test_cli_generate_invalid_name(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    result = main(["generate", "model", "lower_case", "name:str"])
    assert result == 1
    assert "PascalCase" in capsys.readouterr().err


def test_cli_g_alias(tmp_path, monkeypatch):
    """g is an alias for generate."""
    monkeypatch.chdir(tmp_path)
    result = main(["g", "model", "Tag", "name:str"])
    assert result == 0
