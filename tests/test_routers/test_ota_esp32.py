"""ESP32 OTA: firmware binary upload, check, download, report (ota_esp32_service, firmware_file_service)."""

import base64
import hashlib

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils
from httpx import AsyncClient

from app.config import get_settings
from app.services import firmware_file_service

MAC = "aa:bb:cc:dd:ee:01"


@pytest.fixture(autouse=True)
def firmware_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(firmware_file_service, "FIRMWARE_DIR", tmp_path / "firmware")
    return tmp_path / "firmware"


@pytest.fixture
def signing_key():
    return ec.generate_private_key(ec.SECP256R1())


@pytest.fixture
def server_pubkey(tmp_path, signing_key, monkeypatch):
    pem = signing_key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    f = tmp_path / "fw_pub.pem"
    f.write_bytes(pem)
    monkeypatch.setattr(get_settings(), "firmware_public_key_file", str(f))
    return f


def esp_image(size: int = 4096, chip_id: int = 0x0009) -> bytes:
    header = bytearray(24)
    header[0] = 0xE9
    header[1] = 3
    header[12:14] = chip_id.to_bytes(2, "little")
    body = bytes((i * 7) & 0xFF for i in range(size - len(header)))
    return bytes(header) + body


def sign(key, data: bytes) -> str:
    digest = hashlib.sha256(data).digest()
    return base64.b64encode(key.sign(digest, ec.ECDSA(utils.Prehashed(hashes.SHA256())))).decode()


async def _setup(client: AsyncClient, version: str = "1.1.0", mac: str = MAC):
    dt = (await client.post("/api/device-types", json={"name": "lcd2", "display_name": "ESP32-S3-LCD-2",
                                                        "update_method": "ota_http"})).json()
    dev = (await client.post("/api/devices", json={"device_type_id": dt["id"], "name": "LCD2-1",
                                                   "mac_address": mac})).json()
    fw = (await client.post("/api/firmware", json={"device_type_id": dt["id"], "version": version,
                                                   "changelog": "test release"})).json()
    await client.post(f"/api/firmware/{fw['id']}/latest")
    await client.post(f"/api/firmware/{fw['id']}/stable")
    return dt, dev, fw


async def _upload(client: AsyncClient, fw_id: int, data: bytes, signature: str):
    return await client.post(f"/api/firmware/{fw_id}/binary", files={"file": ("firmware.bin", data)},
                             data={"signature": signature})


async def _enroll(anon: AsyncClient, version: str = "1.0.0") -> tuple[str, dict]:
    resp = await anon.get("/api/ota/esp32/check", params={"mac": MAC, "version": version, "request_token": "true"})
    assert resp.status_code == 200
    data = resp.json()
    return data["device_token"], data


# ── upload ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_binary(client: AsyncClient, signing_key, firmware_dir):
    _, _, fw = await _setup(client)
    data = esp_image()
    resp = await _upload(client, fw["id"], data, sign(signing_key, data))
    assert resp.status_code == 200
    body = resp.json()
    assert body["file_size"] == len(data)
    assert body["file_checksum"] == hashlib.sha256(data).hexdigest()
    assert body["file_signature"]
    assert body["released_at"]
    assert (firmware_dir / str(fw["device_type_id"]) / "1.1.0.bin").read_bytes() == data


@pytest.mark.asyncio
async def test_upload_needs_admin(anon_client: AsyncClient):
    resp = await anon_client.post("/api/firmware/1/binary", files={"file": ("f.bin", b"\xe9")}, data={"signature": "x"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_upload_rejects_non_esp_image(client: AsyncClient, signing_key):
    _, _, fw = await _setup(client)
    data = b"\x7fELF" + b"\x00" * 100
    resp = await _upload(client, fw["id"], data, sign(signing_key, data))
    assert resp.status_code == 400
    assert "0xE9" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_upload_rejects_too_large(client: AsyncClient, signing_key, monkeypatch):
    monkeypatch.setattr(get_settings(), "firmware_max_size", 1000)
    _, _, fw = await _setup(client)
    data = esp_image(2000)
    resp = await _upload(client, fw["id"], data, sign(signing_key, data))
    assert resp.status_code == 413


@pytest.mark.asyncio
async def test_upload_rejects_bad_signature_format(client: AsyncClient):
    _, _, fw = await _setup(client)
    assert (await _upload(client, fw["id"], esp_image(), "not base64!")).status_code == 400
    assert (await _upload(client, fw["id"], esp_image(), base64.b64encode(b"short").decode())).status_code == 400


@pytest.mark.asyncio
async def test_upload_needs_semver_version(client: AsyncClient, signing_key):
    _, _, fw = await _setup(client, version="1.0.0-beta")
    data = esp_image()
    resp = await _upload(client, fw["id"], data, sign(signing_key, data))
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_upload_checks_signature_with_server_key(client: AsyncClient, signing_key, server_pubkey):
    _, _, fw = await _setup(client)
    data = esp_image()
    assert (await _upload(client, fw["id"], data, sign(signing_key, data))).status_code == 200
    other_key = ec.generate_private_key(ec.SECP256R1())
    resp = await _upload(client, fw["id"], data, sign(other_key, data))
    assert resp.status_code == 400
    assert "does not match" in resp.json()["detail"]
    # signed a different file
    resp = await _upload(client, fw["id"], data, sign(signing_key, data + b"x"))
    assert resp.status_code == 400


# ── check / download / report ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_unknown_mac(client: AsyncClient, anon_client: AsyncClient):
    resp = await anon_client.get("/api/ota/esp32/check", params={"mac": "de:ad:be:ef:00:00", "version": "1.0.0",
                                                                 "request_token": "true"})
    assert resp.status_code == 200
    assert resp.json()["update_available"] is False
    assert resp.json()["device_token"] is None


@pytest.mark.asyncio
async def test_check_requires_token(client: AsyncClient, anon_client: AsyncClient):
    """No transition mode for ESP32: a check without a token and without request_token is refused."""
    _, dev, _ = await _setup(client)
    resp = await anon_client.get("/api/ota/esp32/check", params={"mac": MAC, "version": "1.0.0"})
    assert resp.status_code == 401
    events = [e["event"] for e in (await client.get(f"/api/devices/{dev['id']}/auth-events")).json()]
    assert "token_missing" in events


@pytest.mark.asyncio
async def test_full_update_flow(client: AsyncClient, anon_client: AsyncClient, signing_key):
    _, dev, fw = await _setup(client, version="1.1.0")
    data = esp_image(8192)
    sig = sign(signing_key, data)
    assert (await _upload(client, fw["id"], data, sig)).status_code == 200

    token, first = await _enroll(anon_client, "1.0.0")
    assert token
    assert first["update_available"] is True
    assert first["latest_version"] == "1.1.0"
    assert first["firmware_url"] == "/api/ota/esp32/firmware/1.1.0"
    assert first["file_size"] == len(data)
    assert first["file_checksum"] == hashlib.sha256(data).hexdigest()
    assert first["file_signature"] == sig

    h = {"X-Device-Token": token}
    resp = await anon_client.get(first["firmware_url"], params={"mac": MAC}, headers=h)
    assert resp.status_code == 200
    assert resp.content == data

    resp = await anon_client.post("/api/ota/esp32/report", headers=h, json={
        "mac_address": MAC, "from_version": "1.0.0", "to_version": "1.1.0", "status": "completed"})
    assert resp.status_code == 200 and resp.json()["success"] is True
    info = (await client.get(f"/api/devices/{dev['id']}")).json()
    assert info["current_version"] == "1.1.0"
    assert info["has_device_token"] is True

    # Now on the release: nothing more to install
    resp = await anon_client.get("/api/ota/esp32/check", params={"mac": MAC, "version": "1.1.0"}, headers=h)
    assert resp.status_code == 200
    assert resp.json()["update_available"] is False


@pytest.mark.asyncio
async def test_device_ahead_of_release_is_not_downgraded(client: AsyncClient, anon_client: AsyncClient, signing_key):
    _, _, fw = await _setup(client, version="1.1.0")
    data = esp_image()
    await _upload(client, fw["id"], data, sign(signing_key, data))
    token, first = await _enroll(anon_client, "1.2.0")
    assert first["update_available"] is False
    assert first["firmware_url"] is None


@pytest.mark.asyncio
async def test_release_without_binary_is_not_offered(client: AsyncClient, anon_client: AsyncClient):
    await _setup(client, version="1.1.0")   # record only, no .bin uploaded
    _, first = await _enroll(anon_client, "1.0.0")
    assert first["update_available"] is False


@pytest.mark.asyncio
async def test_download_needs_token(client: AsyncClient, anon_client: AsyncClient, signing_key):
    _, _, fw = await _setup(client, version="1.1.0")
    data = esp_image()
    await _upload(client, fw["id"], data, sign(signing_key, data))
    token, _ = await _enroll(anon_client, "1.0.0")
    url = "/api/ota/esp32/firmware/1.1.0"
    assert (await anon_client.get(url, params={"mac": MAC})).status_code == 401
    assert (await anon_client.get(url, params={"mac": MAC}, headers={"X-Device-Token": "guess"})).status_code == 401
    assert (await anon_client.get(url, params={"mac": "de:ad:be:ef:00:00"})).status_code == 404
    assert (await anon_client.get("/api/ota/esp32/firmware/9.9.9", params={"mac": MAC},
                                  headers={"X-Device-Token": token})).status_code == 404


@pytest.mark.asyncio
async def test_mac_case_and_dashes_match(client: AsyncClient, anon_client: AsyncClient):
    await _setup(client, mac="AA:BB:CC:DD:EE:01")
    resp = await anon_client.get("/api/ota/esp32/check", params={"mac": "aa-bb-cc-dd-ee-01", "version": "1.0.0",
                                                                 "request_token": "true"})
    assert resp.status_code == 200
    assert resp.json()["device_token"]


@pytest.mark.asyncio
async def test_report_failed_keeps_version(client: AsyncClient, anon_client: AsyncClient):
    _, dev, _ = await _setup(client)
    token, _ = await _enroll(anon_client, "1.0.0")
    resp = await anon_client.post("/api/ota/esp32/report", headers={"X-Device-Token": token}, json={
        "mac_address": MAC, "from_version": "1.0.0", "to_version": "1.1.0", "status": "rolled_back",
        "error_message": "self test failed"})
    assert resp.status_code == 200
    assert (await client.get(f"/api/devices/{dev['id']}")).json()["current_version"] == "1.0.0"
