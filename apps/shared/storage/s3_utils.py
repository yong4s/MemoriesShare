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
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )
        self.bucket = settings.S3_BUCKET_NAME

    def upload_file(self, file, bucket_name, file_name, folder_name=None):
        try:
            if folder_name:
                s3_key = f"{folder_name}/{file_name}"
            else:
                s3_key = file_name

            self.s3_client.upload_fileobj(file, bucket_name, s3_key)
            file_url = f"https://{bucket_name}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{s3_key}"
            return file_url
        except NoCredentialsError:
            raise Exception("Credentials not available")

    def create_bucket(self, bucket_name):
        self.s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={
                "LocationConstraint": settings.AWS_S3_REGION_NAME
            },
        )
        print(f"Bucket {bucket_name} created successfully")

    def bucket_exists(self, bucket_name):
        response = self.s3_client.list_buckets()
        for bucket in response["Buckets"]:
            if bucket["Name"] == bucket_name:
                return True
        return False

    def create_bucket_if_not_exists(self, bucket_name):
        if self.bucket_exists(bucket_name):
            print(f"Bucket {bucket_name} already exists")
            return True
        else:
            try:
                self.s3_client.create_bucket(bucket_name)
                print(f"Bucket {bucket_name} created successfully")
                return True
            except ClientError as e:
                print(f"Error: {e}")
                return False

    def create_folder(self, folder_name):
        if not folder_name.endswith("/"):
            folder_name += "/"

        try:
            self.s3_client.put_object(Bucket=self.bucket, Key=folder_name)
            return (
                f"Folder '{folder_name}' created successfully in bucket '{self.bucket}'"
            )
        except ClientError as e:
            return f"Error: {e.response['Error']['Message']}"
        except (BotoCoreError, NoCredentialsError) as e:
            return f"AWS configuration error: {e!s}"
        except Exception as e:
            return f"An unexpected error occurred: {e!s}"

    def folder_exists(self, folder_name: str) -> bool:
        response = self.s3_client.list_objects_v2(
            Bucket=self.bucket, Prefix=f"{folder_name}/", Delimiter="/"
        )

        if "Contents" in response and len(response["Contents"]) > 0:
            return True
        return False

    def delete_s3_object(self, object_key):
        s3_client = boto3.client("s3")

        try:
            response = s3_client.delete_object(Bucket=self.bucket, Key=object_key)
            print(f"Object {object_key} deleted from bucket {self.bucket}.")
            return response
        except NoCredentialsError:
            print("Error: Provide valid AWS credentials.")
        except ClientError as e:
            print(f"Error deleting object: {e}")

    def delete_folder(self, folder_name):
        try:
            objects_to_delete = self.s3_client.list_objects_v2(
                Bucket=self.bucket, Prefix=folder_name
            )

            if "Contents" not in objects_to_delete:
                raise S3ServiceError(
                    f"No such folder: {folder_name} in bucket: {self.bucket}"
                )

            delete_objects = [
                {"Key": obj["Key"]} for obj in objects_to_delete["Contents"]
            ]
            response = self.s3_client.delete_objects(
                Bucket=self.bucket, Delete={"Objects": delete_objects}
            )

            if "Errors" in response:
                raise S3ServiceError(
                    f"Failed to delete some objects: {response['Errors']}"
                )

            return True
        except ClientError as e:
            print(f"Error deleting folder {folder_name}: {e}")
            return False

    def list_objects_starting_with(self, prefix):
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
            if "Contents" in response:
                return [obj["Key"] for obj in response["Contents"]]
            return []
        except ClientError as e:
            raise Exception(f"Error listing objects: {e}")

    def generate_presigned_url(self, key, expiration=3600, operation="get_object"):
        try:
            return self.s3_client.generate_presigned_url(
                operation,
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expiration,
            )
        except ClientError as e:
            raise S3ServiceError(f"Error generating presigned URL: {e}")

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
                raise S3ServiceError("S3 key is required")

            if not content_type:
                raise S3ServiceError("Content type is required for security validation")

            S3KeyValidator.validate_file_type(content_type)

            if user_id and event_gallery_url:
                S3KeyValidator.validate_s3_key_format(key, user_id, event_gallery_url)

            if expiration > 86400:
                logger.warning(
                    f"Upload URL expiration time reduced from {expiration} to 86400 seconds"
                )
                expiration = 86400

            params = {"Bucket": self.bucket, "Key": key, "ContentType": content_type}

            url = self.s3_client.generate_presigned_url(
                "put_object",
                Params=params,
                ExpiresIn=expiration,
            )

            logger.info(
                f"Generated secure upload URL for user {user_id}, expires in {expiration}s"
            )
            return url

        except ClientError as e:
            error_msg = f"Error generating upload URL: {e}"
            logger.error(error_msg)
            raise S3ServiceError(error_msg)

    def generate_download_url(
        self, key, expiration=3600, filename=None, user_id=None, event_gallery_url=None
    ):
        try:
            if not key:
                raise S3ServiceError("S3 key is required")

            if user_id and event_gallery_url:
                S3KeyValidator.validate_s3_key_format(key, user_id, event_gallery_url)

            if not self.object_exists(key):
                raise S3ServiceError(f"Object not found: {key}")

            if expiration > 86400:
                logger.warning(
                    f"Download URL expiration time reduced from {expiration} to 86400 seconds"
                )
                expiration = 86400

            params = {"Bucket": self.bucket, "Key": key}

            if filename:
                sanitized_filename = S3KeyValidator.sanitize_filename(filename)
                params["ResponseContentDisposition"] = (
                    f'attachment; filename="{sanitized_filename}"'
                )

            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params=params,
                ExpiresIn=expiration,
            )

            logger.info(
                f"Generated secure download URL for user {user_id}, expires in {expiration}s"
            )
            return url

        except ClientError as e:
            error_msg = f"Error generating download URL: {e}"
            logger.error(error_msg)
            raise S3ServiceError(error_msg)

    def generate_delete_url(self, key, expiration=300):
        try:
            return self.s3_client.generate_presigned_url(
                "delete_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expiration,
            )
        except ClientError as e:
            raise S3ServiceError(f"Error generating delete URL: {e}")

    def object_exists(self, key):
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise S3ServiceError(f"Error checking object existence: {e}")

    def get_object_metadata(self, key):
        try:
            response = self.s3_client.head_object(Bucket=self.bucket, Key=key)
            return {
                "content_type": response.get("ContentType"),
                "content_length": response.get("ContentLength"),
                "last_modified": response.get("LastModified"),
                "etag": response.get("ETag"),
                "metadata": response.get("Metadata", {}),
            }
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise S3ServiceError(f"Object not found: {key}")
            raise S3ServiceError(f"Error getting object metadata: {e}")

    def copy_object(self, source_key, destination_key):
        try:
            copy_source = {"Bucket": self.bucket, "Key": source_key}
            self.s3_client.copy_object(
                CopySource=copy_source, Bucket=self.bucket, Key=destination_key
            )
            return True
        except ClientError as e:
            raise S3ServiceError(f"Error copying object: {e}")

    def generate_bulk_download_urls(self, keys, expiration=3600):
        try:
            urls = {}
            for key in keys:
                urls[key] = self.generate_download_url(key, expiration)
            return urls
        except (ClientError, BotoCoreError) as e:
            raise S3ServiceError(f"AWS error generating bulk download URLs: {e}")
        except Exception as e:
            raise S3ServiceError(f"Unexpected error generating bulk download URLs: {e}")

    def process_uploaded_file(self, s3_key, file_type):
        try:
            file_content = self._download_file_content(s3_key)

            if file_type.startswith("image/"):
                return self._process_image(file_content, s3_key)
            elif file_type.startswith("video/"):
                return self._process_video(file_content, s3_key)
            else:
                return self._process_document(file_content, s3_key)

        except (ClientError, BotoCoreError) as e:
            raise S3ServiceError(f"AWS error processing uploaded file: {e}")
        except (ValueError, TypeError) as e:
            raise S3ServiceError(f"File processing validation error: {e}")
        except Exception as e:
            raise S3ServiceError(f"Unexpected error processing uploaded file: {e}")

    def _download_file_content(self, s3_key):
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=s3_key)
            return response["Body"].read()
        except ClientError as e:
            raise S3ServiceError(f"Error downloading file: {e}")

    def _process_image(self, file_content, s3_key):
        try:
            import io

            from PIL import Image

            image = Image.open(io.BytesIO(file_content))

            thumbnail = image.copy()
            thumbnail.thumbnail((300, 300))

            thumbnail_key = f"{s3_key}_thumb"
            thumbnail_buffer = io.BytesIO()
            thumbnail.save(thumbnail_buffer, format=image.format or "JPEG")
            thumbnail_buffer.seek(0)

            self.s3_client.upload_fileobj(
                thumbnail_buffer,
                self.bucket,
                thumbnail_key,
                ExtraArgs={"ContentType": "image/jpeg"},
            )

            return {
                "original": s3_key,
                "thumbnail": thumbnail_key,
                "dimensions": image.size,
                "format": image.format,
            }

        except ImportError:
            return {"original": s3_key, "processed": False}
        except (ClientError, BotoCoreError) as e:
            raise S3ServiceError(f"AWS error processing image: {e}")
        except (ValueError, OSError) as e:
            raise S3ServiceError(f"Image processing error: {e}")
        except Exception as e:
            raise S3ServiceError(f"Unexpected error processing image: {e}")

    def _process_video(self, file_content, s3_key):
        return {
            "original": s3_key,
            "processed": False,
            "note": "Video processing not implemented yet",
        }

    def _process_document(self, file_content, s3_key):
        return {
            "original": s3_key,
            "processed": False,
            "note": "Document processing not implemented yet",
        }


def file_generate_name(original_file_name):
    extension = pathlib.Path(original_file_name).suffix
    return f"{uuid.uuid4().hex}{extension}"