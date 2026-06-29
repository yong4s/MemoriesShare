"""
UUID Generation Utilities

Centralized UUID generation for consistent format across the application.
"""

import uuid


def generate_event_uuid() -> uuid.UUID:
    """
    Generate a new UUID4 for event entities

    Returns:
        uuid.UUID: A new UUID4 instance for events
    """
    return uuid.uuid4()
