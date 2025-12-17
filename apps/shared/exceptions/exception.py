from rest_framework.exceptions import APIException


class S3UploadException(APIException):
    """Exception raised when S3 file upload fails."""

    status_code = 503
    default_detail = 'Error uploading file in S3'
    default_code = 's3_upload_error'


class S3ServiceError(APIException):
    """Generic S3 service error for infrastructure failures."""

    status_code = 500
    default_detail = 'S3 service error occurred'
    default_code = 's3_service_error'


class S3BucketNotFoundError(APIException):
    """Exception raised when S3 bucket is not found."""

    status_code = 404
    default_detail = 'S3 bucket not found.'
    default_code = 's3_bucket_not_found'


class S3BucketPermissionError(APIException):
    """Exception raised when S3 bucket access is denied."""

    status_code = 403
    default_detail = 'Permission denied for S3 bucket.'
    default_code = 's3_bucket_permission_denied'


class UserNotFoundError(APIException):
    """Generic user not found error for infrastructure queries."""

    status_code = 404
    default_detail = 'User not found.'
    default_code = 'user_not_found'
