import logging
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db import transaction

from apps.accounts.dal.user_dal import UserDAL
from apps.accounts.models.custom_user import CustomUser
from apps.shared.exceptions.user_exceptions import EmailAlreadyExistsError
from apps.shared.exceptions.user_exceptions import UserAuthenticationError
from apps.shared.exceptions.user_exceptions import UserCreationError
from apps.shared.exceptions.user_exceptions import UserNotFoundError
from apps.shared.exceptions.user_exceptions import UserValidationError

logger = logging.getLogger(__name__)


class UserService:
    """Service layer for user operations"""

    def __init__(self, dal: UserDAL = None):
        self.dal = dal or UserDAL()

    # =============================================================================
    # USER CREATION OPERATIONS
    # =============================================================================

    @transaction.atomic
    def create_registered_user(
        self,
        email: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
        **extra_fields,
    ) -> CustomUser:
        """
        Create a fully registered user with email and password.

        Args:
            email: User email address (must be unique)
            password: User password
            first_name: Optional first name
            last_name: Optional last name
            **extra_fields: Additional user fields

        Returns:
            CustomUser instance with is_registered=True

        Raises:
            EmailAlreadyExistsError: If email is already in use
            UserValidationError: If validation fails
            UserCreationError: If creation fails
        """
        try:
            # Validate email uniqueness
            if self.dal.get_by_email(email, registered_only=True):
                raise EmailAlreadyExistsError(
                    f"Registered user with email {email} already exists"
                )

            # Validate input data
            self._validate_registered_user_data(email, password, first_name, last_name)

            # Create user through DAL
            user = self.dal.create_registered_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                **extra_fields,
            )

            logger.info(f"Created registered user: {user.email} (ID: {user.id})")
            return user

        except ValidationError as e:
            logger.error(f"Validation error creating registered user: {e}")
            raise UserValidationError(str(e))
        except IntegrityError as e:
            logger.error(f"Database integrity error creating user: {e}")
            raise EmailAlreadyExistsError("Email address is already in use")
        except Exception as e:
            logger.error(f"Unexpected error creating registered user: {e}")
            raise UserCreationError(f"Failed to create registered user: {e}")

    @transaction.atomic
    def create_guest_user(
        self,
        guest_name: str,
        guest_email: str = "",
        invite_token: str = None,
        **extra_fields,
    ) -> CustomUser:
        """
        Create a guest user for event participation.

        Args:
            guest_name: Display name for the guest
            guest_email: Optional contact email (not for authentication)
            invite_token: Optional invitation token used
            **extra_fields: Additional user fields

        Returns:
            CustomUser instance with is_registered=False

        Raises:
            UserValidationError: If validation fails
            UserCreationError: If creation fails
        """
        try:
            # Validate guest data
            self._validate_guest_user_data(guest_name, guest_email)

            # Create guest user through DAL
            user = self.dal.create_guest_user(
                guest_name=guest_name, invite_token=invite_token, **extra_fields
            )

            logger.info(f"Created guest user: {guest_name} (ID: {user.id})")
            return user

        except ValidationError as e:
            logger.error(f"Validation error creating guest user: {e}")
            raise UserValidationError(str(e))
        except Exception as e:
            logger.error(f"Unexpected error creating guest user: {e}")
            raise UserCreationError(f"Failed to create guest user: {e}")

    @transaction.atomic
    def create_guest_from_invitation(
        self, invite_token: str, guest_name: str, guest_email: str = ""
    ) -> CustomUser:
        """
        Create guest user from invitation token.

        Args:
            invite_token: Valid invitation token
            guest_name: Display name for guest
            guest_email: Optional contact email

        Returns:
            CustomUser instance for guest

        Raises:
            UserValidationError: If token is invalid or data is invalid
            UserCreationError: If creation fails
        """
        try:
            # Validate invitation token
            if not invite_token:
                raise UserValidationError("Invitation token is required")

            # Check if token was already used
            existing_user = self.dal.get_by_invite_token(invite_token)
            if existing_user:
                raise UserValidationError("Invitation token has already been used")

            # Create guest user
            user = self.create_guest_user(
                guest_name=guest_name,
                guest_email=guest_email,
                invite_token=invite_token,
            )

            logger.info(
                f"Created guest user from invitation: {guest_name} (Token: {invite_token[:8]}...)"
            )
            return user

        except UserValidationError:
            raise
        except Exception as e:
            logger.error(f"Error creating guest from invitation: {e}")
            raise UserCreationError(f"Failed to create guest from invitation: {e}")

    # =============================================================================
    # USER CONVERSION OPERATIONS
    # =============================================================================

    @transaction.atomic
    def convert_guest_to_registered(
        self,
        guest_user: CustomUser,
        email: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
    ) -> CustomUser:
        """
        Convert existing guest user to registered user.

        This preserves all existing relationships and event participations
        while upgrading the user to full registered status.

        Args:
            guest_user: Existing guest CustomUser
            email: Email for registration
            password: Password for authentication
            first_name: Optional first name
            last_name: Optional last name

        Returns:
            Updated CustomUser with is_registered=True

        Raises:
            UserValidationError: If user is already registered or validation fails
            EmailAlreadyExistsError: If email is already in use
            UserCreationError: If conversion fails
        """
        try:
            # Validate that user is actually a guest
            if guest_user.is_registered:
                raise UserValidationError("User is already registered")

            # Validate email availability
            if self.dal.get_by_email(email, registered_only=True):
                raise EmailAlreadyExistsError(
                    f"Email {email} is already in use by registered user"
                )

            # Validate registration data
            self._validate_registered_user_data(email, password, first_name, last_name)

            # Convert using model method
            converted_user = guest_user.convert_to_registered(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )

            logger.info(
                f"Converted guest user {guest_user.id} to registered user with email {email}"
            )
            return converted_user

        except ValidationError as e:
            logger.error(f"Validation error converting guest to registered: {e}")
            raise UserValidationError(str(e))
        except EmailAlreadyExistsError:
            raise
        except Exception as e:
            logger.error(f"Error converting guest to registered user: {e}")
            raise UserCreationError(f"Failed to convert guest to registered user: {e}")

    # =============================================================================
    # USER AUTHENTICATION OPERATIONS
    # =============================================================================

    def authenticate_user(self, email: str, password: str) -> CustomUser | None:
        """
        Authenticate registered user by email and password.

        Args:
            email: User email
            password: User password

        Returns:
            CustomUser if authentication successful, None otherwise

        Raises:
            UserAuthenticationError: If authentication fails
        """
        try:
            # Only registered users can authenticate
            user = self.dal.get_by_email(email, registered_only=True)
            if not user:
                logger.warning(
                    f"Authentication attempt for non-existent email: {email}"
                )
                return None

            # Use Django's authenticate
            authenticated_user = authenticate(email=email, password=password)
            if authenticated_user and authenticated_user.is_registered:
                logger.info(f"Successful authentication for user: {email}")
                return authenticated_user

            logger.warning(f"Failed authentication attempt for user: {email}")
            return None

        except Exception as e:
            logger.error(f"Error during authentication for {email}: {e}")
            raise UserAuthenticationError(f"Authentication failed: {e}")

    def verify_guest_access(self, invite_token: str) -> CustomUser | None:
        """
        Verify guest access using invitation token.

        Args:
            invite_token: Invitation token to verify

        Returns:
            CustomUser if token is valid, None otherwise
        """
        try:
            if not invite_token:
                return None

            user = self.dal.get_by_invite_token(invite_token)
            if user and user.is_guest and user.is_active:
                logger.info(f"Valid guest access for token: {invite_token[:8]}...")
                return user

            logger.warning(
                f"Invalid guest access attempt with token: {invite_token[:8]}..."
            )
            return None

        except Exception as e:
            logger.error(f"Error verifying guest access: {e}")
            return None

    # =============================================================================
    # USER QUERY OPERATIONS
    # =============================================================================

    def get_user_by_id(self, user_id: int) -> CustomUser | None:
        """Get user by ID"""
        return self.dal.get_by_id(user_id)

    def get_user_by_email(
        self, email: str, registered_only: bool = True
    ) -> CustomUser | None:
        """Get user by email"""
        return self.dal.get_by_email(email, registered_only=registered_only)

    def get_user_by_uuid(self, user_uuid: str) -> CustomUser | None:
        """Get user by UUID"""
        return self.dal.get_by_uuid(user_uuid)

    def get_registered_users(self, limit: int = None) -> list[CustomUser]:
        """Get list of registered users"""
        return self.dal.get_registered_users(limit=limit)

    def get_guest_users(self, limit: int = None) -> list[CustomUser]:
        """Get list of guest users"""
        return self.dal.get_guest_users(limit=limit)

    def search_users(
        self, query: str, registered_only: bool = True
    ) -> list[CustomUser]:
        """Search users by name or email"""
        return self.dal.search_users(query, registered_only=registered_only)

    # =============================================================================
    # USER PROFILE OPERATIONS
    # =============================================================================

    @transaction.atomic
    def update_user_profile(self, user: CustomUser, **update_fields) -> CustomUser:
        """
        Update user profile information.

        Args:
            user: CustomUser to update
            **update_fields: Fields to update

        Returns:
            Updated CustomUser

        Raises:
            UserValidationError: If validation fails
            UserCreationError: If update fails
        """
        try:
            # Validate update fields
            self._validate_profile_update(user, update_fields)

            # Update through DAL
            updated_user = self.dal.update_user(user, **update_fields)

            logger.info(f"Updated profile for user {user.id}")
            return updated_user

        except ValidationError as e:
            logger.error(f"Validation error updating user profile: {e}")
            raise UserValidationError(str(e))
        except Exception as e:
            logger.error(f"Error updating user profile: {e}")
            raise UserCreationError(f"Failed to update user profile: {e}")

    @transaction.atomic
    def deactivate_user(self, user: CustomUser) -> CustomUser:
        """
        Deactivate user account.

        Args:
            user: CustomUser to deactivate

        Returns:
            Updated CustomUser with is_active=False
        """
        user.is_active = False
        user.save(update_fields=["is_active"])

        logger.info(f"Deactivated user {user.id}")
        return user

    @transaction.atomic
    def reactivate_user(self, user: CustomUser) -> CustomUser:
        """
        Reactivate user account.

        Args:
            user: CustomUser to reactivate

        Returns:
            Updated CustomUser with is_active=True
        """
        user.is_active = True
        user.save(update_fields=["is_active"])

        logger.info(f"Reactivated user {user.id}")
        return user

    # =============================================================================
    # MAINTENANCE OPERATIONS
    # =============================================================================

    def cleanup_inactive_guests(self, days_old: int = 30) -> int:
        """
        Clean up old inactive guest users.

        Args:
            days_old: Remove guests older than this many days

        Returns:
            Number of users deleted
        """
        try:
            deleted_count = self.dal.cleanup_inactive_guests(days_old)
            logger.info(
                f"Cleaned up {deleted_count} inactive guest users older than {days_old} days"
            )
            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up inactive guests: {e}")
            return 0

    def get_user_statistics(self) -> dict[str, int]:
        """
        Get user statistics.

        Returns:
            Dictionary with user counts by type and status
        """
        try:
            stats = {
                "total_users": self.dal.get_user_count(),
                "registered_users": self.dal.get_registered_user_count(),
                "guest_users": self.dal.get_guest_user_count(),
                "active_users": self.dal.get_active_user_count(),
                "inactive_users": self.dal.get_inactive_user_count(),
            }

            logger.debug(f"User statistics: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Error getting user statistics: {e}")
            return {}

    # =============================================================================
    # PRIVATE VALIDATION METHODS
    # =============================================================================

    def _validate_registered_user_data(
        self, email: str, password: str, first_name: str, last_name: str
    ) -> None:
        """Validate data for registered user creation"""
        errors = []

        if not email or "@" not in email:
            errors.append("Valid email address is required")

        if not password or len(password) < 8:
            errors.append("Password must be at least 8 characters long")

        if first_name and len(first_name.strip()) < 1:
            errors.append("First name cannot be empty if provided")

        if last_name and len(last_name.strip()) < 1:
            errors.append("Last name cannot be empty if provided")

        if errors:
            raise ValidationError(errors)

    def _validate_guest_user_data(self, guest_name: str, guest_email: str) -> None:
        """Validate data for guest user creation"""
        errors = []

        if not guest_name or len(guest_name.strip()) < 2:
            errors.append("Guest name must be at least 2 characters long")

        if guest_email and "@" not in guest_email:
            errors.append("Guest email must be a valid email address if provided")

        if errors:
            raise ValidationError(errors)

    def _validate_profile_update(
        self, user: CustomUser, update_fields: dict[str, Any]
    ) -> None:
        """Validate profile update fields"""
        # Prevent changing critical fields
        forbidden_fields = ["id", "user_uuid", "is_registered", "password"]
        for field in forbidden_fields:
            if field in update_fields:
                raise ValidationError(
                    f"Field '{field}' cannot be updated through profile update"
                )

        # Validate email changes for registered users
        if "email" in update_fields and user.is_registered:
            new_email = update_fields["email"]
            if not new_email or "@" not in new_email:
                raise ValidationError(
                    "Valid email address is required for registered users"
                )

            # Check email uniqueness
            existing_user = self.dal.get_by_email(new_email, registered_only=True)
            if existing_user and existing_user.id != user.id:
                raise ValidationError("Email address is already in use")
