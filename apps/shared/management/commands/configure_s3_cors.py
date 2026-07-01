import boto3
from botocore.exceptions import BotoCoreError
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """
    Apply CORS configuration to the S3 bucket for presigned POST uploads from the browser.

    Usage: python manage.py configure_s3_cors
    """

    help = 'Configure CORS on the S3 bucket to allow presigned POST uploads from the frontend'

    def add_arguments(self, parser):
        parser.add_argument(
            '--origins',
            nargs='*',
            help='Additional allowed origins (e.g. https://yourdomain.com)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print the CORS config without applying it',
        )

    def handle(self, *args, **options):
        bucket_name = settings.S3_BUCKET_NAME
        region = settings.AWS_S3_REGION_NAME

        if not bucket_name:
            self.stderr.write(self.style.ERROR('S3_BUCKET_NAME is not configured in settings.'))
            return

        allowed_origins = [
            'http://localhost:3000',
            'http://127.0.0.1:3000',
            'http://localhost:8080',
            'http://127.0.0.1:8080',
        ]

        frontend_url = getattr(settings, 'FRONTEND_URL', '')
        if frontend_url and frontend_url not in allowed_origins:
            allowed_origins.append(frontend_url)

        extra_origins = options.get('origins') or []
        for origin in extra_origins:
            if origin not in allowed_origins:
                allowed_origins.append(origin)

        cors_configuration = {
            'CORSRules': [
                {
                    'AllowedHeaders': ['*'],
                    'AllowedMethods': ['POST', 'PUT', 'GET', 'HEAD'],
                    'AllowedOrigins': allowed_origins,
                    'ExposeHeaders': ['ETag', 'Content-Length', 'Content-Type'],
                    'MaxAgeSeconds': 3600,
                },
            ],
        }

        self.stdout.write(f'Bucket: {bucket_name} ({region})')
        self.stdout.write(f'Allowed origins: {allowed_origins}')
        self.stdout.write('Allowed methods: POST, PUT, GET, HEAD')

        if options['dry_run']:
            self.stdout.write(self.style.WARNING('DRY RUN - CORS config not applied'))
            self.stdout.write(str(cors_configuration))
            return

        try:
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=region,
            )

            s3_client.put_bucket_cors(
                Bucket=bucket_name,
                CORSConfiguration=cors_configuration,
            )

            self.stdout.write(self.style.SUCCESS(f'CORS configured successfully on bucket "{bucket_name}"'))

        except ClientError as e:
            self.stderr.write(self.style.ERROR(f'AWS error: {e}'))
        except BotoCoreError as e:
            self.stderr.write(self.style.ERROR(f'Boto error: {e}'))
