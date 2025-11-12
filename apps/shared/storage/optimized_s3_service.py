"""
Optimized S3 Service for Media Flow Application.

This module provides a comprehensive, production-ready S3 service following
SOLID principles, AWS best practices, and proper error handling.
"""

import json
import logging
from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union
from urllib.parse import quote

import boto3
from botocore.exceptions import BotoCoreError
from botocore.exceptions import ClientError
from botocore.exceptions import NoCredentialsError
from django.conf import settings
from django.core.exceptions import ValidationError

from apps.shared.exceptions.exception import S3ServiceError
from apps.shared.interfaces.service_interfaces import IS3Service
from apps.shared.utils.uuid_utils import S3KeyGenerator
from apps.shared.utils.uuid_utils import UUIDValidator
from apps.shared.utils.validators import FileUploadValidator
from apps.shared.utils.validators import S3KeyValidator

logger = logging.getLogger(__name__)


class S3OperationType(Enum):
    """Enumeration of S3 operation types for URL generation."""

    UPLOAD = 'upload'
    DOWNLOAD = 'download'
    DELETE = 'delete'
    BULK_DOWNLOAD = 'bulk_download'


@dataclass
class S3ExpirationConfig:
    """Configuration for S3 URL expiration times."""

    upload: int = 3600  # 1 hour for uploads
    download: int = 3600  # 1 hour for downloads
    delete: int = 300  # 5 minutes for deletes
    bulk_download: int = 7200  # 2 hours for bulk operations
    max_expiration: int = 86400  # 24 hours maximum


@dataclass
class S3ObjectInfo:
    """Information about an S3 object."""

    key: str
    size: int
    last_modified: str
    etag: str
    content_type: str | None = None


@dataclass
class S3UploadRequest:
    """Request parameters for S3 upload URL generation."""

    s3_key: str
    content_type: str
    expires_in: int | None = None
    metadata: dict[str, str] | None = None
    content_length_range: tuple[int, int] | None = None


class IS3Client(ABC):
    """Abstract interface for S3 client operations."""

    @abstractmethod
    def generate_presigned_post(self, **kwargs) -> dict[str, Any]:
        """Generate presigned POST URL."""

    @abstractmethod
    def generate_presigned_url(self, operation: str, **kwargs) -> str:
        """Generate presigned URL for operation."""

    @abstractmethod
    def head_object(self, **kwargs) -> dict[str, Any]:
        """Get object metadata."""

    @abstractmethod
    def list_objects_v2(self, **kwargs) -> dict[str, Any]:
        """List objects in bucket."""

    @abstractmethod
    def put_object(self, **kwargs) -> dict[str, Any]:
        """Put object to S3."""

    @abstractmethod
    def copy_object(self, **kwargs) -> dict[str, Any]:
        """Copy object in S3."""

    @abstractmethod
    def delete_objects(self, **kwargs) -> dict[str, Any]:
        """Delete multiple objects."""


class BotoS3Client(IS3Client):
    """Boto3 implementation of S3 client interface."""

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

    def copy_object(self, **kwargs) -> dict[str, Any]:
        return self._client.copy_object(**kwargs)

    def delete_objects(self, **kwargs) -> dict[str, Any]:
        return self._client.delete_objects(**kwargs)


class S3ConfigurationManager:
    """Manages S3 configuration and validation."""

    @staticmethod
    def validate_configuration() -> None:
        """Validate required S3 configuration."""
        required_settings = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_S3_REGION_NAME', 'S3_BUCKET_NAME']

        missing_settings = []
        for setting in required_settings:
            if not hasattr(settings, setting) or not getattr(settings, setting):
                missing_settings.append(setting)

        if missing_settings:
            raise S3ServiceError(f"Missing required S3 settings: {', '.join(missing_settings)}")

    @staticmethod
    def create_s3_client() -> boto3.client:
        """Create and configure S3 client."""
        S3ConfigurationManager.validate_configuration()

        try:
            return boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME,
            )
        except (NoCredentialsError, BotoCoreError) as e:
            logger.error(f'Failed to create S3 client: {e}')
            raise S3ServiceError(f'S3 client creation failed: {e}')


class S3KeyManager:
    """Manages S3 key generation and validation."""

    @staticmethod
    def generate_event_structure(user_uuid: str, event_uuid: str) -> dict[str, str]:
        """Generate complete S3 structure for an event."""
        S3KeyManager._validate_uuid(user_uuid, 'user_uuid')
        S3KeyManager._validate_uuid(event_uuid, 'event_uuid')

        base_prefix = S3KeyGenerator.generate_event_prefix(user_uuid, event_uuid)

        return {'base': f'{base_prefix}/', 'albums': f'{base_prefix}/albums/'}

    @staticmethod
    def generate_album_paths(user_uuid: str, event_uuid: str, album_uuid: str) -> dict[str, str]:
        """Generate paths for an album."""
        S3KeyManager._validate_uuid(user_uuid, 'user_uuid')
        S3KeyManager._validate_uuid(event_uuid, 'event_uuid')
        S3KeyManager._validate_uuid(album_uuid, 'album_uuid')

        album_prefix = S3KeyGenerator.generate_album_prefix(user_uuid, event_uuid, album_uuid)

        return {
            'base': f'{album_prefix}/',
            'originals': f'{album_prefix}/originals/',
            'thumbnails': f'{album_prefix}/processed/thumbnails/',
            'compressed': f'{album_prefix}/processed/compressed/',
        }

    @staticmethod
    def _validate_uuid(uuid_value: str, field_name: str) -> None:
        """Validate UUID format."""
        if not UUIDValidator.is_valid_uuid(uuid_value):
            raise S3ServiceError(f'Invalid {field_name}: {uuid_value}')


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
                Bucket=self.bucket_name, Key=request.s3_key, Fields=fields, Conditions=conditions, ExpiresIn=expires_in
            )

            logger.info(f'Generated upload URL for key: {request.s3_key}, ' f'expires in {expires_in}s')
            return response

        except ClientError as e:
            error_msg = f'Error generating upload URL for {request.s3_key}: {e}'
            logger.error(error_msg)
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
            sanitized_filename = S3KeyValidator.sanitize_filename(filename)
            params['ResponseContentDisposition'] = f'attachment; filename="{sanitized_filename}"'

        if response_headers:
            for header, value in response_headers.items():
                params[f'Response{header}'] = value

        try:
            url = self.s3_client.generate_presigned_url('get_object', Params=params, ExpiresIn=expires_in)

            logger.info(f'Generated download URL for key: {s3_key}, ' f'expires in {expires_in}s')
            return url

        except ClientError as e:
            error_msg = f'Error generating download URL for {s3_key}: {e}'
            logger.error(error_msg)
            raise S3ServiceError(error_msg)

    def generate_delete_url(self, s3_key: str, expires_in: int | None = None) -> str:
        """Generate presigned delete URL."""
        self._validate_s3_key(s3_key)

        expires_in = self._normalize_expiration(expires_in, self.config.delete)

        try:
            url = self.s3_client.generate_presigned_url(
                'delete_object', Params={'Bucket': self.bucket_name, 'Key': s3_key}, ExpiresIn=expires_in
            )

            logger.info(f'Generated delete URL for key: {s3_key}, ' f'expires in {expires_in}s')
            return url

        except ClientError as e:
            error_msg = f'Error generating delete URL for {s3_key}: {e}'
            logger.error(error_msg)
            raise S3ServiceError(error_msg)

    def _validate_upload_request(self, request: S3UploadRequest) -> None:
        """Validate upload request parameters."""
        if not request.s3_key:
            raise S3ServiceError('S3 key is required')
        if not request.content_type:
            raise S3ServiceError('Content type is required')

        S3KeyValidator.validate_file_type(request.content_type)

    def _validate_s3_key(self, s3_key: str) -> None:
        """Validate S3 key parameter."""
        if not s3_key:
            raise S3ServiceError('S3 key is required')

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
        self, conditions: list[dict], fields: dict[str, str], metadata: dict[str, str] | None
    ) -> None:
        """Add metadata to upload conditions and fields."""
        if metadata:
            for key, value in metadata.items():
                meta_key = f'x-amz-meta-{key}'
                fields[meta_key] = value
                conditions.append({meta_key: value})


class S3ObjectManager:
    """Manages S3 object operations."""

    def __init__(self, s3_client: IS3Client, bucket_name: str):
        self.s3_client = s3_client
        self.bucket_name = bucket_name

    def object_exists(self, s3_key: str) -> bool:
        """Check if object exists in S3."""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.error(f'Error checking object existence for {s3_key}: {e}')
            raise S3ServiceError(f'Error checking object existence: {e}')

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
                raise S3ServiceError(f'Object not found: {s3_key}')
            logger.error(f'Error getting metadata for {s3_key}: {e}')
            raise S3ServiceError(f'Error getting object metadata: {e}')

    def list_objects_with_prefix(self, prefix: str, max_keys: int = 1000) -> list[S3ObjectInfo]:
        """List objects with given prefix."""
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix, MaxKeys=max_keys)

            objects = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    objects.append(
                        S3ObjectInfo(
                            key=obj['Key'],
                            size=obj['Size'],
                            last_modified=obj['LastModified'].isoformat(),
                            etag=obj['ETag'],
                        )
                    )

            return objects

        except ClientError as e:
            error_msg = f'Error listing objects with prefix {prefix}: {e}'
            logger.error(error_msg)
            raise S3ServiceError(error_msg)

    def copy_object_with_metadata(
        self, source_key: str, destination_key: str, metadata: dict[str, str] | None = None
    ) -> bool:
        """Copy object with new metadata."""
        try:
            copy_source = {'Bucket': self.bucket_name, 'Key': source_key}
            extra_args = {}

            if metadata:
                extra_args['Metadata'] = metadata
                extra_args['MetadataDirective'] = 'REPLACE'

            self.s3_client.copy_object(
                CopySource=copy_source, Bucket=self.bucket_name, Key=destination_key, **extra_args
            )

            logger.info(f'Copied {source_key} to {destination_key}')
            return True

        except ClientError as e:
            error_msg = f'Error copying {source_key} to {destination_key}: {e}'
            logger.error(error_msg)
            raise S3ServiceError(error_msg)

    def delete_objects_with_prefix(self, prefix: str) -> int:
        """Delete all objects with given prefix."""
        try:
            objects = self.list_objects_with_prefix(prefix)

            if not objects:
                logger.info(f'No objects found with prefix: {prefix}')
                return 0

            delete_objects = [{'Key': obj.key} for obj in objects]

            response = self.s3_client.delete_objects(Bucket=self.bucket_name, Delete={'Objects': delete_objects})

            deleted_count = len(response.get('Deleted', []))

            if 'Errors' in response:
                logger.error(f"Failed to delete some objects: {response['Errors']}")

            logger.info(f'Deleted {deleted_count} objects with prefix: {prefix}')
            return deleted_count

        except ClientError as e:
            error_msg = f'Error deleting objects with prefix {prefix}: {e}'
            logger.error(error_msg)
            raise S3ServiceError(error_msg)


class S3FolderManager:
    """Manages S3 folder operations."""

    def __init__(self, s3_client: IS3Client, bucket_name: str):
        self.s3_client = s3_client
        self.bucket_name = bucket_name

    def create_folder(self, folder_path: str) -> bool:
        """Create folder in S3 (empty object with trailing slash)."""
        try:
            if not folder_path.endswith('/'):
                folder_path += '/'

            self.s3_client.put_object(
                Bucket=self.bucket_name, Key=folder_path, Body=b'', ContentType='application/x-directory'
            )

            logger.info(f'Created folder: {folder_path}')
            return True

        except ClientError as e:
            error_msg = f'Error creating folder {folder_path}: {e}'
            logger.error(error_msg)
            raise S3ServiceError(error_msg)

    def folder_exists(self, folder_path: str) -> bool:
        """Check if folder exists in S3."""
        try:
            if not folder_path.endswith('/'):
                folder_path += '/'

            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=folder_path, MaxKeys=1)

            return 'Contents' in response or 'CommonPrefixes' in response

        except ClientError as e:
            logger.error(f'Error checking folder existence for {folder_path}: {e}')
            return False

    def create_event_folders(self, user_uuid: str, event_uuid: str) -> bool:
        """Create all necessary folders for an event."""
        try:
            structure = S3KeyManager.generate_event_structure(user_uuid, event_uuid)

            for folder_type, folder_path in structure.items():
                if not self.folder_exists(folder_path):
                    self.create_folder(folder_path)

            logger.info(f'Created all folders for event {event_uuid}')
            return True

        except (ClientError, BotoCoreError) as e:
            error_msg = f'AWS error creating event folders for {event_uuid}: {e}'
            logger.error(error_msg)
            raise S3ServiceError(error_msg)
        except Exception as e:
            error_msg = f'Unexpected error creating event folders for {event_uuid}: {e}'
            logger.exception(error_msg)
            raise S3ServiceError(error_msg)

    def delete_folder(self, folder_path: str) -> int:
        """
        Delete folder and all its contents.

        Args:
            folder_path: Path to folder to delete

        Returns:
            int: Number of objects deleted
        """
        try:
            if not folder_path.endswith('/'):
                folder_path += '/'

            # List and delete all objects in the folder
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=folder_path)

            if 'Contents' not in response:
                logger.info(f'No objects found in folder: {folder_path}')
                return 0

            delete_objects = [{'Key': obj['Key']} for obj in response['Contents']]

            delete_response = self.s3_client.delete_objects(Bucket=self.bucket_name, Delete={'Objects': delete_objects})

            deleted_count = len(delete_response.get('Deleted', []))

            if 'Errors' in delete_response:
                logger.error(f"Failed to delete some objects in {folder_path}: " f"{delete_response['Errors']}")

            logger.info(f'Deleted folder {folder_path} with {deleted_count} objects')
            return deleted_count

        except ClientError as e:
            error_msg = f'Error deleting folder {folder_path}: {e}'
            logger.error(error_msg)
            raise S3ServiceError(error_msg)


class OptimizedS3Service(IS3Service):
    """
    Professional S3 service implementing SOLID principles and AWS best practices.

    This service provides comprehensive S3 operations including:
    - Presigned URL generation for upload/download/delete
    - Object and folder management
    - Bulk operations
    - Proper error handling and logging
    """

    def __init__(self, s3_client: IS3Client | None = None, config: S3ExpirationConfig | None = None):
        """Initialize S3 service with dependency injection support."""
        self.bucket_name = getattr(settings, 'S3_BUCKET_NAME', '')
        self.config = config or S3ExpirationConfig()

        # Dependency injection for testing
        if s3_client:
            self.s3_client = s3_client
        else:
            boto_client = S3ConfigurationManager.create_s3_client()
            self.s3_client = BotoS3Client(boto_client)

        # Initialize managers
        self.url_generator = S3URLGenerator(self.s3_client, self.bucket_name, self.config)
        self.object_manager = S3ObjectManager(self.s3_client, self.bucket_name)
        self.folder_manager = S3FolderManager(self.s3_client, self.bucket_name)

    # === STRUCTURE GENERATION ===

    def generate_event_structure(self, user_uuid: str, event_uuid: str) -> dict[str, str]:
        """Generate complete S3 structure for an event."""
        return S3KeyManager.generate_event_structure(user_uuid, event_uuid)

    def generate_album_paths(self, user_uuid: str, event_uuid: str, album_uuid: str) -> dict[str, str]:
        """Generate paths for an album."""
        return S3KeyManager.generate_album_paths(user_uuid, event_uuid, album_uuid)

    # === PRESIGNED URLS ===

    def generate_presigned_upload_url(
        self,
        s3_key: str,
        content_type: str,
        expires_in: int | None = None,
        metadata: dict[str, str] | None = None,
        content_length_range: tuple[int, int] | None = None,
    ) -> dict[str, Any]:
        """Generate presigned upload URL with advanced options."""
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
        """Generate presigned download URL."""
        # Verify object exists before generating URL
        if not self.object_manager.object_exists(s3_key):
            raise S3ServiceError(f'Object not found: {s3_key}')

        return self.url_generator.generate_download_url(s3_key, expires_in, filename, response_headers)

    def generate_presigned_delete_url(self, s3_key: str, expires_in: int | None = None) -> str:
        """Generate presigned delete URL."""
        return self.url_generator.generate_delete_url(s3_key, expires_in)

    # === BULK OPERATIONS ===

    def generate_bulk_download_urls(self, s3_keys: list[str], expires_in: int | None = None) -> dict[str, str]:
        """Generate presigned URLs for multiple files."""
        try:
            expires_in = expires_in or self.config.bulk_download
            urls = {}

            for s3_key in s3_keys:
                if self.object_manager.object_exists(s3_key):
                    urls[s3_key] = self.url_generator.generate_download_url(s3_key, expires_in)
                else:
                    logger.warning(f'Skipping non-existent key: {s3_key}')

            logger.info(f'Generated {len(urls)} bulk download URLs')
            return urls

        except (ClientError, BotoCoreError) as e:
            error_msg = f'AWS error generating bulk download URLs: {e}'
            logger.error(error_msg)
            raise S3ServiceError(error_msg)
        except Exception as e:
            error_msg = f'Unexpected error generating bulk download URLs: {e}'
            logger.exception(error_msg)
            raise S3ServiceError(error_msg)

    # === OBJECT OPERATIONS ===

    def object_exists(self, s3_key: str) -> bool:
        """Check if object exists in S3."""
        return self.object_manager.object_exists(s3_key)

    def get_object_metadata(self, s3_key: str) -> dict[str, Any]:
        """Get object metadata."""
        return self.object_manager.get_object_metadata(s3_key)

    def list_objects_with_prefix(self, prefix: str, max_keys: int = 1000) -> list[S3ObjectInfo]:
        """List objects with given prefix."""
        return self.object_manager.list_objects_with_prefix(prefix, max_keys)

    def copy_object_with_metadata(
        self, source_key: str, destination_key: str, metadata: dict[str, str] | None = None
    ) -> bool:
        """Copy object with new metadata."""
        return self.object_manager.copy_object_with_metadata(source_key, destination_key, metadata)

    def delete_objects_with_prefix(self, prefix: str) -> int:
        """Delete all objects with given prefix."""
        return self.object_manager.delete_objects_with_prefix(prefix)

    # === FOLDER OPERATIONS ===

    def create_folder(self, folder_path: str) -> bool:
        """Create folder in S3."""
        return self.folder_manager.create_folder(folder_path)

    def folder_exists(self, folder_path: str) -> bool:
        """Check if folder exists in S3."""
        return self.folder_manager.folder_exists(folder_path)

    def create_event_folders(self, user_uuid: str, event_uuid: str) -> bool:
        """Create all necessary folders for an event."""
        return self.folder_manager.create_event_folders(user_uuid, event_uuid)

    def delete_folder(self, folder_path: str) -> int:
        """Delete folder and all its contents."""
        return self.folder_manager.delete_folder(folder_path)
