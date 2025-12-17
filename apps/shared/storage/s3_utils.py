import logging
import pathlib
import re
import uuid

import boto3
from botocore.exceptions import BotoCoreError
from botocore.exceptions import ClientError
from botocore.exceptions import NoCredentialsError
from django.conf import settings

from apps.shared.exceptions.exception import S3ServiceError
from apps.shared.utils.validators import S3KeyValidator

logger = logging.getLogger(__name__)


class S3Service:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )
        self.bucket = settings.S3_BUCKET_NAME

    def upload_file(self, file, bucket_name, file_name, folder_name=None):
        try:
            s3_key = f'{folder_name}/{file_name}' if folder_name else file_name

            self.s3_client.upload_fileobj(file, bucket_name, s3_key)
            return f'https://{bucket_name}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{s3_key}'
        except NoCredentialsError:
            msg = 'Credentials not available'
            raise Exception(msg)

    def create_bucket(self, bucket_name):
        self.s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': settings.AWS_S3_REGION_NAME},
        )

    def bucket_exists(self, bucket_name):
        response = self.s3_client.list_buckets()
        return any(bucket['Name'] == bucket_name for bucket in response['Buckets'])

    def create_bucket_if_not_exists(self, bucket_name):
        if self.bucket_exists(bucket_name):
            return True
        try:
            self.s3_client.create_bucket(bucket_name)
            return True
        except ClientError:
            return False

    def create_folder(self, folder_name):
        if not folder_name.endswith('/'):
            folder_name += '/'

        try:
            self.s3_client.put_object(Bucket=self.bucket, Key=folder_name)
            return f"Folder '{folder_name}' created successfully in bucket '{self.bucket}'"
        except ClientError as e:
            return f"Error: {e.response['Error']['Message']}"
        except (BotoCoreError, NoCredentialsError) as e:
            return f'AWS configuration error: {e!s}'
        except Exception as e:
            return f'An unexpected error occurred: {e!s}'

    def folder_exists(self, folder_name: str) -> bool:
        response = self.s3_client.list_objects_v2(Bucket=self.bucket, Prefix=f'{folder_name}/', Delimiter='/')

        return bool('Contents' in response and len(response['Contents']) > 0)

    def delete_s3_object(self, object_key):
        s3_client = boto3.client('s3')

        try:
            return s3_client.delete_object(Bucket=self.bucket, Key=object_key)
        except NoCredentialsError:
            pass
        except ClientError:
            pass

    def delete_folder(self, folder_name):
        try:
            objects_to_delete = self.s3_client.list_objects_v2(Bucket=self.bucket, Prefix=folder_name)

            if 'Contents' not in objects_to_delete:
                msg = f'No such folder: {folder_name} in bucket: {self.bucket}'
                raise S3ServiceError(msg)

            delete_objects = [{'Key': obj['Key']} for obj in objects_to_delete['Contents']]
            response = self.s3_client.delete_objects(Bucket=self.bucket, Delete={'Objects': delete_objects})

            if 'Errors' in response:
                msg = f"Failed to delete some objects: {response['Errors']}"
                raise S3ServiceError(msg)

            return True
        except ClientError:
            return False

    def list_objects_starting_with(self, prefix):
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
            if 'Contents' in response:
                return [obj['Key'] for obj in response['Contents']]
            return []
        except ClientError as e:
            msg = f'Error listing objects: {e}'
            raise Exception(msg)

    def generate_presigned_url(self, key, expiration=3600, operation='get_object'):
        try:
            return self.s3_client.generate_presigned_url(
                operation,
                Params={'Bucket': self.bucket, 'Key': key},
                ExpiresIn=expiration,
            )
        except ClientError as e:
            msg = f'Error generating presigned URL: {e}'
            raise S3ServiceError(msg)

    def generate_upload_url(
        self,
        key,
        expiration=3600,
        content_type=None,
        user_id=None,
        event_gallery_url=None,
    ):
        try:
            if not key:
                msg = 'S3 key is required'
                raise S3ServiceError(msg)

            if not content_type:
                msg = 'Content type is required for security validation'
                raise S3ServiceError(msg)

            S3KeyValidator.validate_file_type(content_type)

            if user_id and event_gallery_url:
                S3KeyValidator.validate_s3_key_format(key, user_id, event_gallery_url)

            if expiration > 86400:
                logger.warning(f'Upload URL expiration time reduced from {expiration} to 86400 seconds')
                expiration = 86400

            params = {'Bucket': self.bucket, 'Key': key, 'ContentType': content_type}

            url = self.s3_client.generate_presigned_url(
                'put_object',
                Params=params,
                ExpiresIn=expiration,
            )

            logger.info(f'Generated secure upload URL for user {user_id}, expires in {expiration}s')
            return url

        except ClientError as e:
            error_msg = f'Error generating upload URL: {e}'
            logger.exception(error_msg)
            raise S3ServiceError(error_msg)

    def generate_download_url(self, key, expiration=3600, filename=None, user_id=None, event_gallery_url=None):
        try:
            if not key:
                msg = 'S3 key is required'
                raise S3ServiceError(msg)

            if user_id and event_gallery_url:
                S3KeyValidator.validate_s3_key_format(key, user_id, event_gallery_url)

            if not self.object_exists(key):
                msg = f'Object not found: {key}'
                raise S3ServiceError(msg)

            if expiration > 86400:
                logger.warning(f'Download URL expiration time reduced from {expiration} to 86400 seconds')
                expiration = 86400

            params = {'Bucket': self.bucket, 'Key': key}

            if filename:
                sanitized_filename = S3KeyValidator.sanitize_filename(filename)
                params['ResponseContentDisposition'] = f'attachment; filename="{sanitized_filename}"'

            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params=params,
                ExpiresIn=expiration,
            )

            logger.info(f'Generated secure download URL for user {user_id}, expires in {expiration}s')
            return url

        except ClientError as e:
            error_msg = f'Error generating download URL: {e}'
            logger.exception(error_msg)
            raise S3ServiceError(error_msg)

    def generate_delete_url(self, key, expiration=300):
        try:
            return self.s3_client.generate_presigned_url(
                'delete_object',
                Params={'Bucket': self.bucket, 'Key': key},
                ExpiresIn=expiration,
            )
        except ClientError as e:
            msg = f'Error generating delete URL: {e}'
            raise S3ServiceError(msg)

    def object_exists(self, key):
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            msg = f'Error checking object existence: {e}'
            raise S3ServiceError(msg)

    def get_object_metadata(self, key):
        try:
            response = self.s3_client.head_object(Bucket=self.bucket, Key=key)
            return {
                'content_type': response.get('ContentType'),
                'content_length': response.get('ContentLength'),
                'last_modified': response.get('LastModified'),
                'etag': response.get('ETag'),
                'metadata': response.get('Metadata', {}),
            }
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                msg = f'Object not found: {key}'
                raise S3ServiceError(msg)
            msg = f'Error getting object metadata: {e}'
            raise S3ServiceError(msg)

    def copy_object(self, source_key, destination_key):
        try:
            copy_source = {'Bucket': self.bucket, 'Key': source_key}
            self.s3_client.copy_object(CopySource=copy_source, Bucket=self.bucket, Key=destination_key)
            return True
        except ClientError as e:
            msg = f'Error copying object: {e}'
            raise S3ServiceError(msg)

    def generate_bulk_download_urls(self, keys, expiration=3600):
        try:
            urls = {}
            for key in keys:
                urls[key] = self.generate_download_url(key, expiration)
            return urls
        except (ClientError, BotoCoreError) as e:
            msg = f'AWS error generating bulk download URLs: {e}'
            raise S3ServiceError(msg)
        except Exception as e:
            msg = f'Unexpected error generating bulk download URLs: {e}'
            raise S3ServiceError(msg)

    def process_uploaded_file(self, s3_key, file_type):
        try:
            file_content = self._download_file_content(s3_key)

            if file_type.startswith('image/'):
                return self._process_image(file_content, s3_key)
            if file_type.startswith('video/'):
                return self._process_video(file_content, s3_key)
            return self._process_document(file_content, s3_key)

        except (ClientError, BotoCoreError) as e:
            msg = f'AWS error processing uploaded file: {e}'
            raise S3ServiceError(msg)
        except (ValueError, TypeError) as e:
            msg = f'File processing validation error: {e}'
            raise S3ServiceError(msg)
        except Exception as e:
            msg = f'Unexpected error processing uploaded file: {e}'
            raise S3ServiceError(msg)

    def _download_file_content(self, s3_key):
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=s3_key)
            return response['Body'].read()
        except ClientError as e:
            msg = f'Error downloading file: {e}'
            raise S3ServiceError(msg)

    def _process_image(self, file_content, s3_key):
        try:
            import io

            from PIL import Image

            image = Image.open(io.BytesIO(file_content))

            thumbnail = image.copy()
            thumbnail.thumbnail((300, 300))

            thumbnail_key = f'{s3_key}_thumb'
            thumbnail_buffer = io.BytesIO()
            thumbnail.save(thumbnail_buffer, format=image.format or 'JPEG')
            thumbnail_buffer.seek(0)

            self.s3_client.upload_fileobj(
                thumbnail_buffer,
                self.bucket,
                thumbnail_key,
                ExtraArgs={'ContentType': 'image/jpeg'},
            )

            return {
                'original': s3_key,
                'thumbnail': thumbnail_key,
                'dimensions': image.size,
                'format': image.format,
            }

        except ImportError:
            return {'original': s3_key, 'processed': False}
        except (ClientError, BotoCoreError) as e:
            msg = f'AWS error processing image: {e}'
            raise S3ServiceError(msg)
        except (ValueError, OSError) as e:
            msg = f'Image processing error: {e}'
            raise S3ServiceError(msg)
        except Exception as e:
            msg = f'Unexpected error processing image: {e}'
            raise S3ServiceError(msg)

    def _process_video(self, file_content, s3_key):
        return {
            'original': s3_key,
            'processed': False,
            'note': 'Video processing not implemented yet',
        }

    def _process_document(self, file_content, s3_key):
        return {
            'original': s3_key,
            'processed': False,
            'note': 'Document processing not implemented yet',
        }


def file_generate_name(original_file_name):
    extension = pathlib.Path(original_file_name).suffix
    return f'{uuid.uuid4().hex}{extension}'
