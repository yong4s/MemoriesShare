"""
Permission Interface for Service Decoupling

Provides a minimal interface for permission checking to break circular dependencies.
Services that need permission validation can depend on this interface rather than
concrete permission service implementations.
"""

from abc import ABC
from abc import abstractmethod
from typing import Any


class IPermissionValidator(ABC):
    @abstractmethod
    def validate_owner_access(self, event: Any, user_id: int) -> bool:
        """
        Validate that user is event owner (raises PermissionDenied if not).

        Args:
            event: Event object to check ownership for
            user_id: ID of user to validate

        Returns:
            True if validation passes

        Raises:
            PermissionDenied: If user is not the owner
        """

    @abstractmethod
    def validate_guest_or_owner_access(self, event: Any, user_id: int) -> bool:
        """
        Validate that user is owner or guest (raises PermissionDenied if not).

        Args:
            event: Event object to check access for
            user_id: ID of user to validate

        Returns:
            True if validation passes

        Raises:
            PermissionDenied: If user has no access
        """

    @abstractmethod
    def validate_participant_or_owner_access(self, event: Any, user_id: int) -> bool:
        """
        Validate that user is an actual participant of the event, ignoring is_public.

        Stricter than validate_guest_or_owner_access — public-event readers cannot
        enumerate participant data.

        Args:
            event: Event object to check
            user_id: ID of user to validate

        Returns:
            True if validation passes

        Raises:
            EventPermissionError: If user is not a participant
        """

    @abstractmethod
    def is_event_owner(self, event: Any, user_id: int) -> bool:
        """
        Check if user is event owner (returns boolean, no exception).

        Args:
            event: Event object to check ownership for
            user_id: ID of user to check

        Returns:
            True if user is owner, False otherwise
        """

    @abstractmethod
    def has_event_access(self, event: Any, user_id: int) -> bool:
        """
        Check if user has any access to event (returns boolean, no exception).

        Args:
            event: Event object to check access for
            user_id: ID of user to check

        Returns:
            True if user has access, False otherwise
        """

    @abstractmethod
    def is_user_participant(self, event: Any, user_id: int) -> bool:
        """
        Check if user is an actual participant of the event (any role).

        Args:
            event: Event object to check
            user_id: ID of user to check

        Returns:
            True if user is participant, False otherwise
        """
