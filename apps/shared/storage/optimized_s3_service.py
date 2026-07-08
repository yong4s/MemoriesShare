import logging
from abc import ABC
from abc import abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import boto3
from botocore.exceptions import BotoCoreError
from botocore.exceptions import ClientError
from botocore.exceptions import NoCredentialsError
from django.conf import settings

from apps.shared.exceptions.exception import S3ServiceError
from apps.shared.utils.validators import S3KeyValidator

logger = logging.getLogger(__name__)


@dataclass
class S3ExpirationConfig:
    upload: int = 3600
    download: int = 3600
    delete: int = 300
    bulk_download: int = 7200
    max_expiration: int = 86400


@dataclass
class S3UploadRequest:
    s3_key: str
    content_type: str
    expires_in: int | None = None
    metadata: dict[str, str] | None = None
    content_length_range: tuple[int, int] | None = None


class IS3Client(ABC):
    @abstractmethod
    def generate_presigned_post(self, **kwargs) -> dict[str, Any]:
        pass

    @abstractmethod
    def generate_presigned_url(self, operation: str, **kwargs) -> str:
        pass

    @abstractmethod
    def head_object(self, **kwargs) -> dict[str, Any]:
        pass

    @abstractmethod
    def list_objects_v2(self, **kwargs) -> dict[str, Any]:
        pass

    @abstractmethod
    def put_object(self, **kwargs) -> dict[str, Any]:
        pass

    @abstractmethod
    def get_object(self, **kwargs) -> dict[str, Any]:
        pass

    @abstractmethod
    def delete_objects(self, **kwargs) -> dict[str, Any]:
        pass


class BotoS3Client(IS3Client):
    def __init__(self, s3_client):
        self._client = s3_client

    def generate_presigned_post(self, **kwargs) -> dict[str, Any]:
        return self._client.generate_presigned_post(**kwargs)

    def generate_presigned_url(self, operation: str, **kwargs) -> str:
        return self._client.generate_presigned_url(operation, **kwargs)

    def head_object(self, **kwargs) -> dict[str, Any]:
        return self._client.head_object(**kwargs)

    def list_objects_v2(self, **kwargs) -> dict[str, Any]:
        return self._client.list_objects_v2(**kwargs)

    def put_object(self, **kwargs) -> dict[str, Any]:
        return self._client.put_object(**kwargs)

    def get_object(self, **kwargs) -> dict[str, Any]:
        return self._client.get_object(**kwargs)

    def delete_objects(self, **kwargs) -> dict[str, Any]:
        return self._client.delete_objects(**kwargs)


class S3ConfigurationManager:
    @staticmethod
    def validate_configuration() -> None:
        required_settings = [
            'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY',
            'AWS_S3_REGION_NAME',
            'S3_BUCKET_NAME',
        ]

        missing_settings = []
        for setting in required_settings:
            if not hasattr(settings, setting) or not getattr(settings, setting):
                missing_settings.append(setting)

        if missing_settings:
            msg = f"Missing required S3 settings: {', '.join(missing_settings)}"
            raise S3ServiceError(msg)

    @staticmethod
    def create_s3_client() -> boto3.client:
        S3ConfigurationManager.validate_configuration()

        try:
            return boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME,
            )
        except (NoCredentialsError, BotoCoreError) as e:
            logger.exception(f'Failed to create S3 client: {e}')
            msg = f'S3 client creation failed: {e}'
            raise S3ServiceError(msg)


def _format_content_disposition(filename: str) -> str:
    """Build a safe ``attachment`` Content-Disposition for an arbitrary filename.

    Uses RFC 5987 ``filename*`` (percent-encoded UTF-8) so names with spaces,
    parentheses, or non-ASCII characters download correctly, with an ASCII
    ``filename`` fallback. Both forms are injection-safe: the fallback drops
    control characters, quotes, and non-ASCII; ``filename*`` percent-encodes
    everything unsafe.
    """
    ascii_fallback = ''.join(c for c in filename if 32 <= ord(c) < 127 and c not in '"\\') or 'download'
    rfc5987 = "UTF-8''" + quote(filename, safe='')
    return f'attachment; filename="{ascii_fallback}"; filename*={rfc5987}'


class S3URLGenerator:
    """Handles generation of presigned URLs."""

    def __init__(self, s3_client: IS3Client, bucket_name: str, config: S3ExpirationConfig):
        self.s3_client = s3_client
        self.bucket_name = bucket_name
        self.config = config

    def generate_upload_url(self, request: S3UploadRequest) -> dict[str, Any]:
        """Generate presigned upload URL with advanced options."""
        self._validate_upload_request(request)

        expires_in = self._normalize_expiration(request.expires_in, self.config.upload)

        conditions = [{'Content-Type': request.content_type}]
        fields = {'Content-Type': request.content_type}

        self._add_content_length_constraint(conditions, request.content_length_range)
        self._add_metadata_to_upload(conditions, fields, request.metadata)

        try:
            response = self.s3_client.generate_presigned_post(
                Bucket=self.bucket_name,
                Key=request.s3_key,
                Fields=fields,
                Conditions=conditions,
                ExpiresIn=expires_in,
            )

            logger.info(f'Generated upload URL for key: {request.s3_key}, ' f'expires in {expires_in}s')
            return response

        except ClientError as e:
            error_msg = f'Error generating upload URL for {request.s3_key}: {e}'
            logger.exception(error_msg)
            raise S3ServiceError(error_msg)

    def generate_download_url(
        self,
        s3_key: str,
        expires_in: int | None = None,
        filename: str | None = None,
        response_headers: dict[str, str] | None = None,
    ) -> str:
        """Generate presigned download URL."""
        self._validate_s3_key(s3_key)

        expires_in = self._normalize_expiration(expires_in, self.config.download)
        params = {'Bucket': self.bucket_name, 'Key': s3_key}

        if filename:
            params['ResponseContentDisposition'] = _format_content_disposition(filename)

        if response_headers:
            for header, value in response_headers.items():
                params[f'Response{header}'] = value

        try:
            url = self.s3_client.generate_presigned_url('get_object', Params=params, ExpiresIn=expires_in)

            logger.info(f'Generated download URL for key: {s3_key}, ' f'expires in {expires_in}s')
            return url

        except ClientError as e:
            error_msg = f'Error generating download URL for {s3_key}: {e}'
            logger.exception(error_msg)
            raise S3ServiceError(error_msg)

    def _validate_upload_request(self, request: S3UploadRequest) -> None:
        """Validate upload request parameters."""
        if not request.s3_key:
            msg = 'S3 key is required'
            raise S3ServiceError(msg)
        if not request.content_type:
            msg = 'Content type is required'
            raise S3ServiceError(msg)

        S3KeyValidator.validate_file_type(request.content_type)

    def _validate_s3_key(self, s3_key: str) -> None:
        """Validate S3 key parameter."""
        if not s3_key:
            msg = 'S3 key is required'
            raise S3ServiceError(msg)

    def _normalize_expiration(self, expires_in: int | None, default: int) -> int:
        """Normalize and validate expiration time."""
        expires_in = expires_in or default

        if expires_in > self.config.max_expiration:
            logger.warning(f'Expiration time reduced from {expires_in} to ' f'{self.config.max_expiration} seconds')
            expires_in = self.config.max_expiration

        return expires_in

    def _add_content_length_constraint(
        self, conditions: list[dict], content_length_range: tuple[int, int] | None
    ) -> None:
        """Add content length constraints to upload conditions."""
        if content_length_range:
            min_size, max_size = content_length_range
            conditions.append(['content-length-range', min_size, max_size])
        else:
            # Default: 1 byte - 100MB
            conditions.append(['content-length-range', 1, 100 * 1024 * 1024])

    def _add_metadata_to_upload(
        self,
        conditions: list[dict],
        fields: dict[str, str],
        metadata: dict[str, str] | None,
    ) -> None:
        """Add metadata to upload conditions and fields."""
        if metadata:
            for key, value in metadata.items():
                meta_key = f'x-amz-meta-{key}'
                fields[meta_key] = value
                conditions.append({meta_key: value})


# S3's DeleteObjects API accepts at most 1000 keys per request.
_S3_DELETE_BATCH_LIMIT = 1000


class S3ObjectManager:
    """Manages S3 object operations."""

    def __init__(self, s3_client: IS3Client, bucket_name: str):
        self.s3_client = s3_client
        self.bucket_name = bucket_name

    def _paginate_objects(self, prefix: str, max_keys: int | None = None) -> Iterator[dict[str, Any]]:
        """Yield raw S3 object dicts under ``prefix``, transparently paginating.

        ``list_objects_v2`` returns at most 1000 objects per page; this follows
        the continuation token until the prefix is exhausted. ``max_keys`` caps
        the total yielded (stopping early); ``None`` streams every object.
        """
        yielded = 0
        continuation_token: str | None = None
        while True:
            kwargs: dict[str, Any] = {'Bucket': self.bucket_name, 'Prefix': prefix}
            if continuation_token:
                kwargs['ContinuationToken'] = continuation_token

            response = self.s3_client.list_objects_v2(**kwargs)

            for obj in response.get('Contents', []):
                yield obj
                yielded += 1
                if max_keys is not None and yielded >= max_keys:
                    return

            if not response.get('IsTruncated'):
                return
            continuation_token = response.get('NextContinuationToken')

    def _delete_keys(self, keys: list[str]) -> int:
        """Delete ``keys`` in batches of 1000 (the DeleteObjects limit), raising on any failure."""
        deleted_count = 0
        errors: list[dict[str, Any]] = []

        for start in range(0, len(keys), _S3_DELETE_BATCH_LIMIT):
            batch = keys[start : start + _S3_DELETE_BATCH_LIMIT]
            response = self.s3_client.delete_objects(
                Bucket=self.bucket_name,
                Delete={'Objects': [{'Key': key} for key in batch]},
            )
            deleted_count += len(response.get('Deleted', []))
            if response.get('Errors'):
                errors.extend(response['Errors'])

        if errors:
            logger.error(f'Failed to delete {len(errors)} object(s): {errors}')
            msg = f'Failed to delete {len(errors)} of {len(keys)} objects'
            raise S3ServiceError(msg)

        return deleted_count

    def object_exists(self, s3_key: str) -> bool:
        """Check if object exists in S3."""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.exception(f'Error checking object existence for {s3_key}: {e}')
            msg = f'Error checking object existence: {e}'
            raise S3ServiceError(msg)

    def get_object_metadata(self, s3_key: str) -> dict[str, Any]:
        """Get object metadata."""
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)

            return {
                'content_type': response.get('ContentType'),
                'content_length': response.get('ContentLength'),
                'last_modified': response.get('LastModified'),
                'etag': response.get('ETag'),
                'metadata': response.get('Metadata', {}),
            }

        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                msg = f'Object not found: {s3_key}'
                raise S3ServiceError(msg)
            logger.exception(f'Error getting metadata for {s3_key}: {e}')
            msg = f'Error getting object metadata: {e}'
            raise S3ServiceError(msg)

    def download_object(self, s3_key: str) -> bytes:
        """Download object bytes from S3."""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            data = response['Body'].read()
            logger.info(f'Downloaded object {s3_key} ({len(data)} bytes)')
            return data
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                msg = f'Object not found: {s3_key}'
                raise S3ServiceError(msg)
            logger.exception(f'Error downloading object {s3_key}: {e}')
            msg = f'Error downloading object: {e}'
            raise S3ServiceError(msg)

    def upload_object(self, s3_key: str, body: bytes, content_type: str) -> None:
        """Upload object bytes to S3."""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=body,
                ContentType=content_type,
            )
            logger.info(f'Uploaded object {s3_key} ({len(body)} bytes, {content_type})')
        except ClientError as e:
            logger.exception(f'Error uploading object {s3_key}: {e}')
            msg = f'Error uploading object: {e}'
            raise S3ServiceError(msg)

    def delete_object(self, s3_key: str) -> int:
        """Delete a single object by its exact key (no prefix expansion)."""
        try:
            response = self.s3_client.delete_objects(
                Bucket=self.bucket_name,
                Delete={'Objects': [{'Key': s3_key}]},
            )

            if response.get('Errors'):
                logger.error(f'Failed to delete object {s3_key}: {response['Errors']}')
                msg = f'Error deleting object: {s3_key}'
                raise S3ServiceError(msg)

            deleted_count = len(response.get('Deleted', []))
            logger.info(f'Deleted object: {s3_key}')
            return deleted_count

        except ClientError as e:
            error_msg = f'Error deleting object {s3_key}: {e}'
            logger.exception(error_msg)
            raise S3ServiceError(error_msg)

    def delete_objects_with_prefix(self, prefix: str) -> int:
        """Delete every object under ``prefix`` (fully paginated, batched ≤1000/request)."""
        try:
            keys = [obj['Key'] for obj in self._paginate_objects(prefix)]

            if not keys:
                logger.info(f'No objects found with prefix: {prefix}')
                return 0

            deleted_count = self._delete_keys(keys)
            logger.info(f'Deleted {deleted_count} objects with prefix: {prefix}')
            return deleted_count

        except ClientError as e:
            error_msg = f'Error deleting objects with prefix {prefix}: {e}'
            logger.exception(error_msg)
            raise S3ServiceError(error_msg)


class S3FolderManager:
    """Manages S3 folder operations."""

    def __init__(self, s3_client: IS3Client, bucket_name: str, object_manager: S3ObjectManager):
        self.s3_client = s3_client
        self.bucket_name = bucket_name
        self.object_manager = object_manager

    def delete_folder(self, folder_path: str) -> int:
        """Delete a folder and all of its contents (fully paginated and batched).

        Args:
            folder_path: Path to folder to delete

        Returns:
            int: Number of objects deleted
        """
        if not folder_path.endswith('/'):
            folder_path += '/'

        deleted_count = self.object_manager.delete_objects_with_prefix(folder_path)
        logger.info(f'Deleted folder {folder_path} with {deleted_count} objects')
        return deleted_count


class OptimizedS3Service:
    def __init__(
        self,
        s3_client: IS3Client | None = None,
        config: S3ExpirationConfig | None = None,
    ):
        self.bucket_name = getattr(settings, 'S3_BUCKET_NAME', '')
        self.config = config or S3ExpirationConfig()

        if s3_client:
            self.s3_client = s3_client
        else:
            boto_client = S3ConfigurationManager.create_s3_client()
            self.s3_client = BotoS3Client(boto_client)

        self.url_generator = S3URLGenerator(self.s3_client, self.bucket_name, self.config)
        self.object_manager = S3ObjectManager(self.s3_client, self.bucket_name)
        self.folder_manager = S3FolderManager(self.s3_client, self.bucket_name, self.object_manager)

    def generate_presigned_upload_url(
        self,
        s3_key: str,
        content_type: str,
        expires_in: int | None = None,
        metadata: dict[str, str] | None = None,
        content_length_range: tuple[int, int] | None = None,
    ) -> dict[str, Any]:
        request = S3UploadRequest(
            s3_key=s3_key,
            content_type=content_type,
            expires_in=expires_in,
            metadata=metadata,
            content_length_range=content_length_range,
        )
        return self.url_generator.generate_upload_url(request)

    def generate_presigned_download_url(
        self,
        s3_key: str,
        expires_in: int | None = None,
        filename: str | None = None,
        response_headers: dict[str, str] | None = None,
    ) -> str:
        """Generate presigned download URL.

        Signing is local and the DB row is authoritative, so we do not pay a
        round-trip ``head_object`` here — a URL for a (rare) missing object
        simply 404s on use, which the client already handles.
        """
        return self.url_generator.generate_download_url(s3_key, expires_in, filename, response_headers)

    def object_exists(self, s3_key: str) -> bool:
        """Check if object exists in S3."""
        return self.object_manager.object_exists(s3_key)

    def get_object_metadata(self, s3_key: str) -> dict[str, Any]:
        """Get object metadata."""
        return self.object_manager.get_object_metadata(s3_key)

    def download_object(self, s3_key: str) -> bytes:
        """Download object bytes from S3."""
        return self.object_manager.download_object(s3_key)

    def upload_object(self, s3_key: str, body: bytes, content_type: str) -> None:
        """Upload object bytes to S3."""
        self.object_manager.upload_object(s3_key, body, content_type)

    def delete_object(self, s3_key: str) -> int:
        """Delete a single object by its exact key (no prefix expansion)."""
        return self.object_manager.delete_object(s3_key)

    def delete_objects_with_prefix(self, prefix: str) -> int:
        """Delete all objects with given prefix."""
        return self.object_manager.delete_objects_with_prefix(prefix)

    def delete_folder(self, folder_path: str) -> int:
        """Delete folder and all its contents."""
        return self.folder_manager.delete_folder(folder_path)


# Module-level singleton — boto3 low-level clients are thread-safe, so one
# instance per process is correct and cheaper than re-creating the boto3
# client on every HTTP request. Tests that need a fresh patched instance
# should set _optimized_s3_service to None before patching the class.
_optimized_s3_service: OptimizedS3Service | None = None


def get_optimized_s3_service() -> OptimizedS3Service:
    """Return the process-wide OptimizedS3Service singleton, creating it lazily."""
    global _optimized_s3_service  # noqa: PLW0603 — intentional lazy singleton init
    if _optimized_s3_service is None:
        _optimized_s3_service = OptimizedS3Service()
    return _optimized_s3_service
