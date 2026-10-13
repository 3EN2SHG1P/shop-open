from pathlib import Path

from core.config import PROJECT_ROOT


def _png_bytes() -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + b"\x00" * 32
        + b"IEND\xaeB`\x82"
    )


def _cleanup_file(client, url: str):
    path = url.split("/uploads/", 1)[-1]
    f = PROJECT_ROOT / "uploads" / path
    if f.is_file():
        f.unlink()


def test_upload_requires_login(client):
    r = client.post("/api/v1/upload", files={"file": ("a.png", _png_bytes(), "image/png")})
    assert r.status_code == 401
    assert r.json()["code"] == 1002


def test_upload_image_ok(client, admin_headers):
    r = client.post(
        "/api/v1/upload",
        files={"file": ("brand-logo.png", _png_bytes(), "image/png")},
        headers=admin_headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["url"].startswith("http://testserver/uploads/")
    assert data["url"].endswith(".png")
    assert data["name"] == "brand-logo.png"
    assert data["size"] > 0
    resp = client.get(data["url"])
    assert resp.status_code == 200
    _cleanup_file(client, data["url"])


def test_upload_rejects_bad_ext(client, admin_headers):
    r = client.post(
        "/api/v1/upload",
        files={"file": ("evil.txt", b"not an image", "text/plain")},
        headers=admin_headers,
    )
    assert r.status_code == 422
    assert r.json()["code"] == 2001


def test_upload_rejects_empty_file(client, admin_headers):
    r = client.post(
        "/api/v1/upload",
        files={"file": ("empty.png", b"", "image/png")},
        headers=admin_headers,
    )
    assert r.status_code == 422
    assert r.json()["code"] == 2001
