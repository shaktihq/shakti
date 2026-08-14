from pathlib import Path

import pytest

from shakti import Shakti
from shakti.testing import TestClient


@pytest.fixture()
def static_dir(tmp_path: Path) -> Path:
    (tmp_path / "app.9f8c1a2b3c.js").write_text("console.log('hashed')")
    (tmp_path / "style.css").write_text("body { color: red; }")
    (tmp_path / "index.html").write_text("<html>spa</html>")
    return tmp_path


def make_app(static_dir: Path, **kwargs) -> Shakti:
    app = Shakti(debug=False)
    app.static("/assets", str(static_dir), **kwargs)
    return app


def test_fingerprinted_asset_gets_immutable_cache_header(static_dir: Path) -> None:
    client = TestClient(make_app(static_dir))
    response = client.get("/assets/app.9f8c1a2b3c.js")
    assert response.status_code == 200
    cache_control = response.headers.get("cache-control")
    assert "immutable" in cache_control
    assert "max-age=31536000" in cache_control


def test_plain_asset_gets_short_lived_cache_header(static_dir: Path) -> None:
    client = TestClient(make_app(static_dir))
    response = client.get("/assets/style.css")
    assert response.status_code == 200
    cache_control = response.headers.get("cache-control")
    assert "immutable" not in cache_control
    assert "max-age=3600" in cache_control


def test_missing_asset_is_a_real_404_not_a_spa_fallback(static_dir: Path) -> None:
    client = TestClient(make_app(static_dir, html=True))
    response = client.get("/assets/does-not-exist.js")
    assert response.status_code == 404


def test_missing_asset_is_404_without_html_mode(static_dir: Path) -> None:
    client = TestClient(make_app(static_dir))
    response = client.get("/assets/nope.png")
    assert response.status_code == 404


def test_spa_fallback_only_applies_to_extensionless_paths(static_dir: Path) -> None:
    client = TestClient(make_app(static_dir, html=True))
    response = client.get("/assets/dashboard")
    assert response.status_code == 200
    assert response.text == "<html>spa</html>"


def test_path_traversal_is_rejected(static_dir: Path) -> None:
    client = TestClient(make_app(static_dir))
    response = client.get("/assets/..%2F..%2Fetc%2Fpasswd")
    assert response.status_code in (404, 400)


def test_etag_supports_conditional_304(static_dir: Path) -> None:
    client = TestClient(make_app(static_dir))
    first = client.get("/assets/style.css")
    etag = first.headers.get("etag")
    assert etag
    second = client.get("/assets/style.css", headers={"if-none-match": etag})
    assert second.status_code == 304
