import types

import pytest

from routers import updates


def test_semver_ordering():
    assert updates._semver("v1.2.3") == (1, 2, 3)
    assert updates._semver("v10.0.0") > updates._semver("v2.9.9")
    assert updates._semver("v1.2.3") > updates._semver("v1.2.2")
    assert updates._semver("dev") == (0,)


def test_current_version_dev_without_file(tmp_path, monkeypatch):
    monkeypatch.setattr(updates, "sys", types.SimpleNamespace())
    monkeypatch.chdir(tmp_path)
    v = updates.current_version()
    assert v == "dev"


def test_current_version_reads_bundle_file(tmp_path, monkeypatch):
    f = tmp_path / "version.txt"
    f.write_text("v1.2.0", encoding="utf-8")
    monkeypatch.setattr(updates, "sys", types.SimpleNamespace(frozen=True, _MEIPASS=str(tmp_path), executable=str(tmp_path / "PrestamoFlow.exe")))
    assert updates.current_version() == "v1.2.0"


def test_updates_offline_is_safe(client):
    r = client.get("/api/updates")
    assert r.status_code == 200
    data = r.json()
    assert data["version"] == "dev"
    assert data["update"] is False


def test_updates_aviso_solo_con_version_mayor(client, monkeypatch):
    monkeypatch.setattr(updates, "current_version", lambda: "v1.0.0")
    monkeypatch.setattr(updates, "fetch_latest", lambda: {
        "tag": "v1.1.2", "url": "https://github.com/fake/Setup.exe", "html_url": "https://github.com/release",
    })
    r = client.get("/api/updates")
    assert r.status_code == 200
    data = r.json()
    assert data["update"] is True
    assert data["latest"] == "v1.1.2"
    assert data["url"].startswith("https://")


def test_updates_no_aviso_con_versiones_no_mayores(client, monkeypatch):
    monkeypatch.setattr(updates, "current_version", lambda: "v2.0.0")
    monkeypatch.setattr(updates, "fetch_latest", lambda: {"tag": "v1.1.2", "url": "", "html_url": ""})
    assert client.get("/api/updates").json()["update"] is False


def test_download_sin_instalador_publicado(client, monkeypatch):
    monkeypatch.setattr(updates, "fetch_latest", lambda: {"tag": "v9.9.9", "url": "", "html_url": ""})
    r = client.post("/api/updates/download")
    assert r.status_code == 409