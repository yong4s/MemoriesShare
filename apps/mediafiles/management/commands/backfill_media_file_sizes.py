"""Populate MediaFile.file_size for rows uploaded before the field existed.

For each MediaFile with file_size == 0, head_objects S3 to read the actual
ContentLength and writes it back. Rate-limits via batch sleep so we don't
saturate S3 head_object calls.

Usage:
    python manage.py backfill_media_file_sizes              # all 0-size rows
    python manage.py backfill_media_file_sizes --dry-run    # report only
    python manage.py backfill_media_file_sizes --batch-size 100
"""

import logging
import time

from django.core.management.base import BaseCommand

from apps.mediafiles.models.media_file import MediaFile
from apps.shared.container import get_s3_service

logger = logging.getLogger(__name__)

BATCH_SIZE = 50
BATCH_DELAY_SECONDS = 1


class Command(BaseCommand):
    help = 'Backfill MediaFile.file_size from S3 ContentLength for rows that still report 0.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report counts without writing to the database.',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=BATCH_SIZE,
            help=f'Rows per S3 batch before sleeping (default: {BATCH_SIZE}).',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        batch_size = options['batch_size']

        queryset = MediaFile.objects.filter(file_size=0).only(
            'mediafilePK',
            'file_uuid',
            'S3_object_key',
            'file_size',
        )
        total = queryset.count()
        self.stdout.write(f'Found {total} MediaFile row(s) with file_size=0.')

        if dry_run or total == 0:
            return

        s3_service = get_s3_service()
        updated = 0
        failed = 0

        for index, media_file in enumerate(queryset.iterator(chunk_size=batch_size), start=1):
            try:
                metadata = s3_service.get_object_metadata(media_file.S3_object_key)
                size = int(metadata.get('content_length') or 0)
                if size > 0:
                    MediaFile.objects.filter(pk=media_file.pk).update(file_size=size)
                    updated += 1
                else:
                    logger.warning(
                        'S3 head_object returned 0 ContentLength for %s (key=%s)',
                        media_file.file_uuid,
                        media_file.S3_object_key,
                    )
                    failed += 1
            except Exception:
                logger.exception(
                    'Backfill failed for %s (key=%s)',
                    media_file.file_uuid,
                    media_file.S3_object_key,
                )
                failed += 1

            if index % batch_size == 0:
                self.stdout.write(f'  …processed {index}/{total} (updated={updated}, failed={failed})')
                time.sleep(BATCH_DELAY_SECONDS)

        self.stdout.write(
            self.style.SUCCESS(
                f'Backfill complete: updated={updated} failed={failed} total={total}',
            ),
        )
