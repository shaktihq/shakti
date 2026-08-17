import json
from pathlib import Path

import pytest

from shakti import Shakti
from shakti.staticfiles import StaticFiles
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


# ---------------------------------------------------------------------------
# immutable_manifest — manifest-aware cache detection
# ---------------------------------------------------------------------------

@pytest.fixture()
def manifest_static_dir(tmp_path: Path) -> Path:
    (tmp_path / "app.4889e19a.js").write_text("console.log('real build output')")
    (tmp_path / "app.a1b2c3d4.css").write_text("body{}")
    (tmp_path / "logo.deadbeef.png").write_bytes(b"\x89PNG")
    # Looks fingerprinted by the regex heuristic, but is NOT a real build
    # artifact — e.g. a user-uploaded file that happens to have a
    # hash-like name. The manifest is what must prevent this from being
    # cached as immutable.
    (tmp_path / "coupon.1234abcd.json").write_text('{"code": "SAVE10"}')
    (tmp_path / "index.html").write_text("<html>app</html>")
    return tmp_path


def test_manifest_dict_vite_style_marks_only_listed_files_immutable(manifest_static_dir: Path) -> None:
    manifest = {
        "src/main.ts": {
            "file": "app.4889e19a.js",
            "css": ["app.a1b2c3d4.css"],
            "assets": ["logo.deadbeef.png"],
        },
    }
    app = Shakti(debug=False)
    app.static("/assets", str(manifest_static_dir), immutable_manifest=manifest)
    client = TestClient(app)

    for path in ("app.4889e19a.js", "app.a1b2c3d4.css", "logo.deadbeef.png"):
        r = client.get(f"/assets/{path}")
        assert "immutable" in r.headers.get("cache-control"), path

    # Matches the fingerprint regex but isn't in the manifest — must NOT
    # be treated as immutable. This is the exact false-positive the
    # manifest is meant to prevent.
    r = client.get("/assets/coupon.1234abcd.json")
    assert "immutable" not in r.headers.get("cache-control")
    assert "max-age=3600" in r.headers.get("cache-control")


def test_manifest_dict_flat_webpack_style(manifest_static_dir: Path) -> None:
    manifest = {"main.js": "app.4889e19a.js", "main.css": "app.a1b2c3d4.css"}
    app = Shakti(debug=False)
    app.static("/assets", str(manifest_static_dir), immutable_manifest=manifest)
    client = TestClient(app)

    r = client.get("/assets/app.4889e19a.js")
    assert "immutable" in r.headers.get("cache-control")

    r = client.get("/assets/coupon.1234abcd.json")
    assert "immutable" not in r.headers.get("cache-control")


def test_manifest_iterable_of_filenames(manifest_static_dir: Path) -> None:
    app = Shakti(debug=False)
    app.static(
        "/assets", str(manifest_static_dir),
        immutable_manifest={"app.4889e19a.js"},
    )
    client = TestClient(app)

    r = client.get("/assets/app.4889e19a.js")
    assert "immutable" in r.headers.get("cache-control")

    r = client.get("/assets/app.a1b2c3d4.css")
    assert "immutable" not in r.headers.get("cache-control")


def test_manifest_loaded_from_json_file_path(manifest_static_dir: Path, tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({
        "src/main.ts": {"file": "app.4889e19a.js"},
    }))
    app = Shakti(debug=False)
    app.static("/assets", str(manifest_static_dir), immutable_manifest=str(manifest_path))
    client = TestClient(app)

    r = client.get("/assets/app.4889e19a.js")
    assert "immutable" in r.headers.get("cache-control")
    r = client.get("/assets/app.a1b2c3d4.css")
    assert "immutable" not in r.headers.get("cache-control")


def test_no_manifest_falls_back_to_regex_heuristic(manifest_static_dir: Path) -> None:
    """Default behavior (no immutable_manifest) is unchanged: anything
    that looks hash-fingerprinted, including the coupon file, is treated
    as immutable — this is exactly the imprecision the manifest exists
    to fix, so it must be preserved as the opt-in default."""
    app = Shakti(debug=False)
    app.static("/assets", str(manifest_static_dir))
    client = TestClient(app)

    r = client.get("/assets/coupon.1234abcd.json")
    assert "immutable" in r.headers.get("cache-control")


def test_rolling_deployment_old_hashed_file_not_in_new_manifest_is_safe() -> None:
    """A file from a superseded build (still on disk, e.g. during a
    rolling-deploy grace window) isn't in the *current* manifest, so it
    loses immutable status — a caching-efficiency cost, not a
    correctness one: the file is still served with the right bytes,
    just with a shorter cache lifetime."""
    static = StaticFiles.__new__(StaticFiles)
    static._immutable_names = {"app.NEWHASH01.js"}
    static.max_age = 3600
    static.immutable_max_age = 31_536_000

    assert static._is_immutable("app.NEWHASH01.js") is True
    assert static._is_immutable("app.OLDHASH99.js") is False
