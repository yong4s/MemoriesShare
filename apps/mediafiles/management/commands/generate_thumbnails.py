import logging
import time

from django.core.management.base import BaseCommand

from apps.mediafiles.models.media_file import MediaFile
from apps.mediafiles.tasks import generate_thumbnail_task
from apps.mediafiles.utils.thumbnail import IMAGE_MIME_TYPES

logger = logging.getLogger(__name__)

BATCH_SIZE = 50
BATCH_DELAY_SECONDS = 1


class Command(BaseCommand):
    help = 'Generate thumbnails for existing image files that are missing thumbnails.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview how many files would be processed without dispatching tasks.',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=BATCH_SIZE,
            help=f'Number of tasks to dispatch per batch (default: {BATCH_SIZE}).',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        batch_size = options['batch_size']

        image_files = MediaFile.objects.filter(file_type__in=IMAGE_MIME_TYPES).values_list(
            'file_uuid', flat=True
        )
        total = image_files.count()

        if total == 0:
            self.stdout.write(self.style.WARNING('No image files found.'))
            return

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f'[DRY RUN] Would dispatch {total} thumbnail generation tasks.'))
            return

        self.stdout.write(f'Dispatching thumbnail generation for {total} image files...')

        dispatched = 0
        for i, file_uuid in enumerate(image_files.iterator()):
            generate_thumbnail_task.delay(str(file_uuid))
            dispatched += 1

            if (i + 1) % batch_size == 0:
                self.stdout.write(f'  Dispatched {dispatched}/{total}...')
                time.sleep(BATCH_DELAY_SECONDS)

        self.stdout.write(self.style.SUCCESS(f'Done. Dispatched {dispatched} thumbnail generation tasks.'))
