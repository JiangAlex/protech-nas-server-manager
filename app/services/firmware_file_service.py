"""ESP32 firmware binaries: storage, checks on upload, signature.

Storage: /app/data/artifacts/firmware/<device_type_id>/<version>.bin (the artifacts volume), so two
device types may use the same version number. Versions must be "x.y.z", which also keeps the path
safe.

Checks on upload:
- size between 1 byte and FIRMWARE_MAX_SIZE (one OTA app partition)
- ESP application image: first byte 0xE9; the chip id of the image header is reported
- signature: base64 of a DER ECDSA signature over the SHA-256 of the file (release_fw.py on the
  build PC signs with the private key, the device verifies with the public key it carries). When
  FIRMWARE_PUBLIC_KEY_FILE is set, the server verifies it too and refuses a mismatch, so a release
  mistake shows up at upload time and not on the device.
"""

import base64
import binascii
import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import structlog
from fastapi import HTTPException, UploadFile

from app.config import get_settings
from app.services import version_util

logger = structlog.get_logger()

FIRMWARE_DIR = Path("/app/data/artifacts/firmware")
ESP_IMAGE_MAGIC = 0xE9
CHUNK = 64 * 1024
# esp_chip_id_t in the image header (offset 12, little endian)
CHIP_NAMES = {0x0000: "ESP32", 0x0002: "ESP32-S2", 0x0005: "ESP32-C3", 0x0009: "ESP32-S3",
              0x000C: "ESP32-C2", 0x000D: "ESP32-C6", 0x0010: "ESP32-H2"}


@dataclass
class StoredBinary:
    path: str
    size: int
    sha256: str
    chip: str


def binary_path(device_type_id: int, version: str) -> Path:
    if version_util.parse(version) is None:
        raise HTTPException(status_code=400, detail="Firmware binaries need a version like 1.2.3")
    return FIRMWARE_DIR / str(int(device_type_id)) / f"{version}.bin"


def _decode_signature(signature_b64: str) -> bytes:
    try:
        sig = base64.b64decode(signature_b64.strip(), validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="Signature must be base64")
    # DER ECDSA P-256 signature: SEQUENCE of two INTEGERs, 8..72 bytes
    if not (8 <= len(sig) <= 72) or sig[0] != 0x30:
        raise HTTPException(status_code=400, detail="Signature must be a DER ECDSA signature")
    return sig


def _verify_signature(digest: bytes, sig: bytes) -> None:
    key_file = get_settings().firmware_public_key_file
    if not key_file:
        return
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec, utils

    try:
        key = serialization.load_pem_public_key(Path(key_file).read_bytes())
    except (OSError, ValueError) as e:
        logger.error("firmware_public_key_unreadable", file=key_file, error=str(e))
        raise HTTPException(status_code=500, detail="Server firmware public key is not readable")
    if not isinstance(key, ec.EllipticCurvePublicKey):
        raise HTTPException(status_code=500, detail="Server firmware public key is not an EC key")
    try:
        key.verify(sig, digest, ec.ECDSA(utils.Prehashed(hashes.SHA256())))
    except InvalidSignature:
        raise HTTPException(status_code=400, detail="Signature does not match the file (wrong key or file)")


async def save_binary(device_type_id: int, version: str, upload: UploadFile, signature_b64: str) -> StoredBinary:
    """Check and store an uploaded .bin; returns its path, size, SHA-256 (hex) and chip name."""
    dest = binary_path(device_type_id, version)
    sig = _decode_signature(signature_b64)
    max_size = get_settings().firmware_max_size
    dest.parent.mkdir(parents=True, exist_ok=True)

    sha = hashlib.sha256()
    size = 0
    header = b""
    fd, tmp = tempfile.mkstemp(prefix=".upload-", suffix=".bin", dir=str(dest.parent))
    try:
        with os.fdopen(fd, "wb") as out:
            while True:
                chunk = await upload.read(CHUNK)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_size:
                    raise HTTPException(status_code=413, detail=f"Firmware larger than {max_size} bytes")
                if len(header) < 16:
                    header += chunk[: 16 - len(header)]
                sha.update(chunk)
                out.write(chunk)
        if size == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        if header[0] != ESP_IMAGE_MAGIC or len(header) < 16:
            raise HTTPException(status_code=400, detail="Not an ESP application image (first byte must be 0xE9)")
        digest = sha.digest()
        _verify_signature(digest, sig)
        os.replace(tmp, dest)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise

    chip_id = int.from_bytes(header[12:14], "little")
    chip = CHIP_NAMES.get(chip_id, f"chip 0x{chip_id:04x}")
    logger.info("firmware_binary_saved", device_type_id=device_type_id, version=version, size=size,
                sha256=sha.hexdigest()[:12], chip=chip)
    return StoredBinary(path=str(dest), size=size, sha256=sha.hexdigest(), chip=chip)


def stored_file(path: Optional[str]) -> Optional[Path]:
    """The stored binary when it still exists inside FIRMWARE_DIR, else None."""
    if not path:
        return None
    p = Path(path)
    try:
        p.resolve().relative_to(FIRMWARE_DIR.resolve())
    except ValueError:
        return None
    return p if p.is_file() else None
