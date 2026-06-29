import uuid
from typing import Protocol

import base62


class S3KeyGenerator:
    """Utility for generating S3 keys with optimal key distribution."""

    @staticmethod
    def generate_user_prefix(user_uuid: str) -> str:
        """Generate the S3 prefix for a user."""
        return f'users/{user_uuid}'

    @staticmethod
    def generate_event_prefix(user_uuid: str, event_uuid: str) -> str:
        """Generate the S3 prefix for an event."""
        return f'users/{user_uuid}/events/{event_uuid}'

    @staticmethod
    def generate_album_prefix(user_uuid: str, event_uuid: str, album_uuid: str) -> str:
        """Generate the S3 prefix for an album."""
        return f'users/{user_uuid}/events/{event_uuid}/albums/{album_uuid}'

    @staticmethod
    def generate_file_key(
        user_uuid: str,
        event_uuid: str,
        album_uuid: str,
        file_uuid: str,
        file_extension: str,
        file_type: str = 'originals',
    ) -> str:
        """
        Generate the full S3 key for a file.

        Args:
            user_uuid: User UUID
            event_uuid: Event UUID
            album_uuid: Album UUID
            file_uuid: File UUID
            file_extension: File extension (.jpg, .mp4, etc.)
            file_type: File type (originals, thumbnails, compressed)
        """
        album_prefix = S3KeyGenerator.generate_album_prefix(user_uuid, event_uuid, album_uuid)
        return f'{album_prefix}/{file_type}/{file_uuid}{file_extension}'

    @staticmethod
    def parse_s3_key(s3_key: str) -> dict:
        """
        Parse an S3 key and extract its components.

        Returns:
            dict: Dictionary with the key components
        """
        parts = s3_key.split('/')

        try:
            if len(parts) >= 4 and parts[0] == 'users' and parts[2] == 'events':
                result = {
                    'user_uuid': parts[1],
                    'event_uuid': parts[3],
                    'type': 'event',
                }

                if len(parts) >= 6 and parts[4] == 'albums':
                    result.update({'album_uuid': parts[5], 'type': 'album'})

                    if len(parts) >= 8:
                        result.update({
                            'file_type': parts[6],  # originals, thumbnails, compressed
                            'filename': parts[7],
                            'type': 'file',
                        })

                elif len(parts) >= 6 and parts[4] == 'metadata':
                    result.update({
                        'metadata_type': parts[5].replace('.json', ''),
                        'type': 'metadata',
                    })

                return result

        except (IndexError, ValueError):
            pass

        return {'type': 'unknown', 'raw_key': s3_key}


class UUIDValidator:
    """Validator for UUID fields."""

    @staticmethod
    def is_valid_uuid(uuid_string: str) -> bool:
        """Check whether the string is a valid UUID."""
        try:
            uuid.UUID(uuid_string)
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def is_valid_short_uuid(short_uuid: str) -> bool:
        """Check whether the string is a valid short UUID."""
        try:
            base62.decode(short_uuid)
            return len(short_uuid) >= 6  # minimum length
        except (ValueError, TypeError):
            return False

    @staticmethod
    def validate_s3_key_structure(s3_key: str) -> bool:
        """Validate the structure of an S3 key."""
        parsed = S3KeyGenerator.parse_s3_key(s3_key)
        return parsed['type'] != 'unknown'
