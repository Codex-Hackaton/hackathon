from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import RLock
from typing import Protocol
from uuid import uuid4

from .domain import DomainError


ALLOWED_IMAGE_CONTENT_TYPES = frozenset(
    {"image/jpeg", "image/png", "image/heic", "image/heif"}
)
MAX_PROOF_BYTES = 8 * 1024 * 1024


class UploadSlotError(DomainError):
    pass


@dataclass(slots=True)
class UploadSlot:
    token: str
    image_key: str
    owner_user_id: str
    content_type: str
    expires_at: datetime
    upload_url: str | None = None
    uploaded: bool = False


class ProofStorage(Protocol):
    def create_slot(
        self,
        *,
        owner_user_id: str,
        content_type: str,
        now: datetime | None = None,
    ) -> UploadSlot: ...

    def upload(
        self,
        *,
        token: str,
        content_type: str,
        body: bytes,
        now: datetime | None = None,
    ) -> UploadSlot: ...

    def require_uploaded(self, *, image_key: str, owner_user_id: str) -> UploadSlot: ...

    def path_for(self, image_key: str) -> Path: ...


class LocalProofStorage:
    """Filesystem-backed development adapter mirroring an S3 presigned PUT flow."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path("/tmp/offmate-proof-uploads")
        self.root.mkdir(parents=True, exist_ok=True)
        self._slots: dict[str, UploadSlot] = {}
        self._keys: dict[str, UploadSlot] = {}
        self._lock = RLock()

    def create_slot(
        self,
        *,
        owner_user_id: str,
        content_type: str,
        now: datetime | None = None,
    ) -> UploadSlot:
        if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
            raise UploadSlotError("unsupported proof image content type")
        current_time = now or datetime.now(UTC)
        token = uuid4().hex
        extension = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/heic": "heic",
            "image/heif": "heif",
        }[content_type]
        image_key = f"proofs/{owner_user_id}/{uuid4().hex}.{extension}"
        slot = UploadSlot(
            token=token,
            image_key=image_key,
            owner_user_id=owner_user_id,
            content_type=content_type,
            expires_at=current_time + timedelta(minutes=10),
        )
        with self._lock:
            self._slots[token] = slot
            self._keys[image_key] = slot
        return slot

    def upload(
        self,
        *,
        token: str,
        content_type: str,
        body: bytes,
        now: datetime | None = None,
    ) -> UploadSlot:
        with self._lock:
            slot = self._get_slot(token)
            current_time = now or datetime.now(UTC)
            if current_time >= slot.expires_at:
                raise UploadSlotError("upload slot has expired")
            if slot.uploaded:
                raise UploadSlotError("upload slot has already been used")
            if content_type != slot.content_type:
                raise UploadSlotError("content type does not match the upload slot")
            if not body:
                raise UploadSlotError("proof image is empty")
            if len(body) > MAX_PROOF_BYTES:
                raise UploadSlotError("proof image exceeds 8 MB")

            destination = self.root / slot.image_key
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(body)
            slot.uploaded = True
            return slot

    def require_uploaded(self, *, image_key: str, owner_user_id: str) -> UploadSlot:
        with self._lock:
            try:
                slot = self._keys[image_key]
            except KeyError as error:
                raise UploadSlotError("unknown image_key") from error
            if slot.owner_user_id != owner_user_id:
                raise UploadSlotError("image_key belongs to another user")
            if not slot.uploaded:
                raise UploadSlotError("proof image upload is incomplete")
            return slot

    def path_for(self, image_key: str) -> Path:
        slot = self._keys.get(image_key)
        if slot is None or not slot.uploaded:
            raise UploadSlotError("proof image is unavailable")
        return self.root / image_key

    def _get_slot(self, token: str) -> UploadSlot:
        try:
            return self._slots[token]
        except KeyError as error:
            raise UploadSlotError("upload slot not found") from error


class S3ProofStorage:
    """S3 adapter using a short-lived presigned PUT URL for proof images."""

    def __init__(
        self,
        bucket_name: str,
        *,
        client=None,
        cache_root: Path | None = None,
    ) -> None:
        if not bucket_name:
            raise ValueError("bucket_name is required")
        if client is None:
            import boto3

            client = boto3.client("s3")
        self.bucket_name = bucket_name
        self._client = client
        self._cache_root = cache_root or Path("/tmp/offmate-s3-proofs")
        self._cache_root.mkdir(parents=True, exist_ok=True)

    def create_slot(
        self,
        *,
        owner_user_id: str,
        content_type: str,
        now: datetime | None = None,
    ) -> UploadSlot:
        if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
            raise UploadSlotError("unsupported proof image content type")
        current_time = now or datetime.now(UTC)
        extension = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/heic": "heic",
            "image/heif": "heif",
        }[content_type]
        safe_owner = owner_user_id.replace("/", "_")
        image_key = f"proofs/{safe_owner}/{uuid4().hex}.{extension}"
        upload_url = self._client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": image_key,
                "ContentType": content_type,
            },
            ExpiresIn=600,
        )
        return UploadSlot(
            token="s3",
            image_key=image_key,
            owner_user_id=owner_user_id,
            content_type=content_type,
            expires_at=current_time + timedelta(minutes=10),
            upload_url=upload_url,
        )

    def upload(
        self,
        *,
        token: str,
        content_type: str,
        body: bytes,
        now: datetime | None = None,
    ) -> UploadSlot:
        raise UploadSlotError("use the S3 presigned upload URL")

    def require_uploaded(self, *, image_key: str, owner_user_id: str) -> UploadSlot:
        safe_owner = owner_user_id.replace("/", "_")
        if not image_key.startswith(f"proofs/{safe_owner}/"):
            raise UploadSlotError("image_key belongs to another user")
        try:
            metadata = self._client.head_object(
                Bucket=self.bucket_name,
                Key=image_key,
            )
        except Exception as error:
            raise UploadSlotError("proof image upload is incomplete") from error
        content_type = metadata.get("ContentType", "")
        size = int(metadata.get("ContentLength", 0))
        if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
            raise UploadSlotError("unsupported proof image content type")
        if size <= 0 or size > MAX_PROOF_BYTES:
            raise UploadSlotError("proof image size is invalid")
        return UploadSlot(
            token="s3",
            image_key=image_key,
            owner_user_id=owner_user_id,
            content_type=content_type,
            expires_at=datetime.now(UTC),
            uploaded=True,
        )

    def path_for(self, image_key: str) -> Path:
        suffix = Path(image_key).suffix or ".img"
        destination = self._cache_root / f"{uuid4().hex}{suffix}"
        try:
            self._client.download_file(
                self.bucket_name,
                image_key,
                str(destination),
            )
        except Exception as error:
            raise UploadSlotError("proof image is unavailable") from error
        return destination
