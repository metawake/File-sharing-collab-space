"""
Storage abstraction layer for file persistence.
Allows easy migration from local filesystem to S3/GCS without changing business logic.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO, Optional
import shutil


class StorageBackend(ABC):
    """Abstract interface for file storage operations."""

    @abstractmethod
    async def save(self, key: str, file_data: BinaryIO) -> str:
        """
        Save file data and return storage path/key.

        Args:
            key: Unique identifier for the file (e.g., "users/123/abc123.pdf")
            file_data: Binary file stream

        Returns:
            Storage path or URL
        """
        pass

    @abstractmethod
    async def read(self, key: str) -> bytes:
        """
        Read file contents.

        Args:
            key: Storage key from save()

        Returns:
            File contents as bytes
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete a file.

        Args:
            key: Storage key from save()

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a file exists."""
        pass

    @abstractmethod
    def get_url(self, key: str) -> str:
        """
        Get a URL/path for serving the file.
        For local: absolute file path
        For S3: signed URL or public URL
        """
        pass


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage implementation."""

    def __init__(self, base_dir: str):
        """
        Args:
            base_dir: Root directory for file storage
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, key: str) -> Path:
        """Convert storage key to filesystem path."""
        # Ensure key doesn't escape base_dir
        safe_key = key.replace("..", "").lstrip("/")
        return self.base_dir / safe_key

    async def save(self, key: str, file_data: BinaryIO) -> str:
        """Save file to local filesystem."""
        path = self._resolve_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "wb") as f:
            shutil.copyfileobj(file_data, f)

        return str(path)

    async def read(self, key: str) -> bytes:
        """Read file from local filesystem."""
        path = self._resolve_path(key)
        with open(path, "rb") as f:
            return f.read()

    async def delete(self, key: str) -> bool:
        """Delete file from local filesystem."""
        path = self._resolve_path(key)
        if path.exists():
            path.unlink()
            return True
        return False

    async def exists(self, key: str) -> bool:
        """Check if file exists on local filesystem."""
        return self._resolve_path(key).exists()

    def get_url(self, key: str) -> str:
        """Return absolute file path for local serving."""
        return str(self._resolve_path(key))


# Example S3 implementation (not yet functional, needs boto3)
class S3StorageBackend(StorageBackend):
    """
    S3-compatible storage implementation.

    To use:
    1. Add boto3 to requirements.txt
    2. Set env: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET_NAME
    3. Update config.py to instantiate S3StorageBackend instead of LocalStorageBackend
    """

    def __init__(self, bucket_name: str, region: str = "us-east-1"):
        """
        Args:
            bucket_name: S3 bucket name
            region: AWS region
        """
        self.bucket_name = bucket_name
        self.region = region
        # self.client = boto3.client('s3', region_name=region)

    async def save(self, key: str, file_data: BinaryIO) -> str:
        """Upload file to S3."""
        # self.client.upload_fileobj(file_data, self.bucket_name, key)
        # return f"s3://{self.bucket_name}/{key}"
        raise NotImplementedError("S3 backend requires boto3 implementation")

    async def read(self, key: str) -> bytes:
        """Download file from S3."""
        # response = self.client.get_object(Bucket=self.bucket_name, Key=key)
        # return response['Body'].read()
        raise NotImplementedError("S3 backend requires boto3 implementation")

    async def delete(self, key: str) -> bool:
        """Delete file from S3."""
        # self.client.delete_object(Bucket=self.bucket_name, Key=key)
        # return True
        raise NotImplementedError("S3 backend requires boto3 implementation")

    async def exists(self, key: str) -> bool:
        """Check if file exists in S3."""
        # try:
        #     self.client.head_object(Bucket=self.bucket_name, Key=key)
        #     return True
        # except ClientError:
        #     return False
        raise NotImplementedError("S3 backend requires boto3 implementation")

    def get_url(self, key: str) -> str:
        """Generate presigned URL for S3 object."""
        # return self.client.generate_presigned_url(
        #     'get_object',
        #     Params={'Bucket': self.bucket_name, 'Key': key},
        #     ExpiresIn=3600  # 1 hour
        # )
        raise NotImplementedError("S3 backend requires boto3 implementation")


def get_storage_backend(storage_type: str = "local", **kwargs) -> StorageBackend:
    """
    Factory function to get the configured storage backend.

    Args:
        storage_type: "local" or "s3"
        **kwargs: Backend-specific configuration

    Returns:
        Configured StorageBackend instance

    Example:
        # Local development
        storage = get_storage_backend("local", base_dir="./storage")

        # Production with S3
        storage = get_storage_backend("s3", bucket_name="my-dataroom", region="us-west-2")
    """
    if storage_type == "local":
        return LocalStorageBackend(base_dir=kwargs.get("base_dir", "./storage"))
    elif storage_type == "s3":
        return S3StorageBackend(
            bucket_name=kwargs["bucket_name"], region=kwargs.get("region", "us-east-1")
        )
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")
