"""
Core Service Interfaces

Defines abstract interfaces for the main service classes to enable
dependency inversion, better testing, and architectural flexibility.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from django.core.paginator import Page


class IEventService(ABC):
    """
    Interface for event business logic operations.
    
    This interface defines the contract for event-related business operations,
    allowing for different implementations and easier testing.
    """
    
    @abstractmethod
    def create_event(self, validated_data: Dict[str, Any], user: Any) -> Any:
        """
        Create new event with automatic owner participation.
        
        Args:
            validated_data: Event creation data
            user: Event creator (owner)
            
        Returns:
            Created event instance
        """
        pass
    
    @abstractmethod
    def get_event_detail(self, event_uuid: str, user_id: int) -> Any:
        """
        Get event details with permission check.
        
        Args:
            event_uuid: Event UUID
            user_id: Requesting user ID
            
        Returns:
            Event instance with optimized data
        """
        pass
    
    @abstractmethod
    def get_events_list(self, filters: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """
        Get paginated list of user's events.
        
        Args:
            filters: Query filters and pagination params
            user_id: User ID
            
        Returns:
            Dict containing events and pagination info
        """
        pass
    
    @abstractmethod
    def update_event(self, event_uuid: str, validated_data: Dict[str, Any], user_id: int) -> Any:
        """
        Update existing event.
        
        Args:
            event_uuid: Event UUID
            validated_data: Update data
            user_id: Requesting user ID
            
        Returns:
            Updated event instance
        """
        pass
    
    @abstractmethod
    def delete_event(self, event_uuid: str, user_id: int) -> bool:
        """
        Delete event (only by owner).
        
        Args:
            event_uuid: Event UUID
            user_id: Requesting user ID
            
        Returns:
            True if deleted successfully
        """
        pass
    
    @abstractmethod
    def get_event_participants(
        self, 
        event_uuid: str, 
        requesting_user_id: int, 
        role_filter: Optional[str] = None, 
        rsvp_filter: Optional[str] = None
    ) -> List[Any]:
        """
        Get event participants with permission check.
        
        Args:
            event_uuid: Event UUID
            requesting_user_id: User requesting the list
            role_filter: Optional role filter
            rsvp_filter: Optional RSVP status filter
            
        Returns:
            List of EventParticipant instances
        """
        pass
    
    @abstractmethod
    def add_participant_to_event(
        self, 
        event_uuid: str, 
        user: Any, 
        role: str = 'GUEST',
        **kwargs
    ) -> Any:
        """
        Add participant to event.
        
        Args:
            event_uuid: Event UUID
            user: User to add as participant
            role: Participant role
            **kwargs: Additional parameters
            
        Returns:
            Created participation record
        """
        pass


class IAlbumService(ABC):
    """
    Interface for album business logic operations.
    
    Defines the contract for album-related business operations
    including S3 integration and permission management.
    """
    
    @abstractmethod
    def create_album(self, serializer: Any, event: Any, user_id: int) -> Any:
        """
        Create album for event with validation and S3 integration.
        
        Args:
            serializer: Album creation serializer
            event: Event object
            user_id: User ID
            
        Returns:
            Created album instance
        """
        pass
    
    @abstractmethod
    def get_album(self, user_id: int, album_id: int) -> Any:
        """
        Get album with permission check.
        
        Args:
            user_id: User ID
            album_id: Album ID
            
        Returns:
            Album instance
        """
        pass
    
    @abstractmethod
    def get_albums_for_event(self, user_id: int, event_id: int) -> List[Any]:
        """
        Get albums for event with permission check.
        
        Args:
            user_id: User ID
            event_id: Event ID
            
        Returns:
            List of album instances
        """
        pass
    
    @abstractmethod
    def update_album(self, user_id: int, album_id: int, album_data: Dict[str, Any]) -> Any:
        """
        Update album with owner permission check.
        
        Args:
            user_id: User ID
            album_id: Album ID
            album_data: Update data
            
        Returns:
            Updated album instance
        """
        pass
    
    @abstractmethod
    def delete_album(self, user_id: int, album_id: int) -> bool:
        """
        Delete album with S3 cleanup and permission check.
        
        Args:
            user_id: User ID
            album_id: Album ID
            
        Returns:
            True if deleted successfully
        """
        pass


class IUserService(ABC):
    """
    Interface for user management operations.
    
    Defines the contract for user creation, authentication, and profile management
    for both registered and guest users.
    """
    
    @abstractmethod
    def create_registered_user(
        self, 
        email: str, 
        password: str, 
        first_name: str = '', 
        last_name: str = '', 
        **extra_fields
    ) -> Any:
        """
        Create a fully registered user with email and password.
        
        Args:
            email: User email address
            password: User password
            first_name: Optional first name
            last_name: Optional last name
            **extra_fields: Additional user fields
            
        Returns:
            CustomUser instance with is_registered=True
        """
        pass
    
    @abstractmethod
    def create_guest_user(
        self, 
        guest_name: str, 
        guest_email: str = '', 
        invite_token: Optional[str] = None, 
        **extra_fields
    ) -> Any:
        """
        Create a guest user for event participation.
        
        Args:
            guest_name: Display name for the guest
            guest_email: Optional contact email
            invite_token: Optional invitation token
            **extra_fields: Additional user fields
            
        Returns:
            CustomUser instance with is_registered=False
        """
        pass
    
    @abstractmethod
    def authenticate_user(self, email: str, password: str) -> Optional[Any]:
        """
        Authenticate registered user by email and password.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            CustomUser if authentication successful, None otherwise
        """
        pass
    
    @abstractmethod
    def get_user_by_id(self, user_id: int) -> Optional[Any]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User instance or None
        """
        pass


class IS3Service(ABC):
    """
    Interface for S3 storage operations.
    
    Defines the contract for S3 operations including presigned URLs,
    object management, and folder operations.
    """
    
    @abstractmethod
    def generate_presigned_upload_url(
        self,
        s3_key: str,
        content_type: str,
        expires_in: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate presigned upload URL.
        
        Args:
            s3_key: S3 object key
            content_type: File content type
            expires_in: Optional expiration time
            **kwargs: Additional parameters
            
        Returns:
            Presigned POST data
        """
        pass
    
    @abstractmethod
    def generate_presigned_download_url(
        self,
        s3_key: str,
        expires_in: Optional[int] = None,
        filename: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate presigned download URL.
        
        Args:
            s3_key: S3 object key
            expires_in: Optional expiration time
            filename: Optional filename for download
            **kwargs: Additional parameters
            
        Returns:
            Presigned URL string
        """
        pass
    
    @abstractmethod
    def create_folder(self, folder_path: str) -> bool:
        """
        Create folder in S3.
        
        Args:
            folder_path: Path to folder to create
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    def delete_folder(self, folder_path: str) -> int:
        """
        Delete folder and all its contents.
        
        Args:
            folder_path: Path to folder to delete
            
        Returns:
            Number of objects deleted
        """
        pass
    
    @abstractmethod
    def object_exists(self, s3_key: str) -> bool:
        """
        Check if object exists in S3.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            True if object exists
        """
        pass


class IDataAccessLayer(ABC):
    """
    Interface for data access layer operations.
    
    Defines the contract for database operations with proper abstraction
    from ORM-specific details.
    """
    
    @abstractmethod
    def create(self, model_data: Dict[str, Any]) -> Any:
        """
        Create new model instance.
        
        Args:
            model_data: Data for model creation
            
        Returns:
            Created model instance
        """
        pass
    
    @abstractmethod
    def get_by_id(self, model_id: int) -> Optional[Any]:
        """
        Get model instance by ID.
        
        Args:
            model_id: Model ID
            
        Returns:
            Model instance or None
        """
        pass
    
    @abstractmethod
    def update(self, instance: Any, update_data: Dict[str, Any]) -> Any:
        """
        Update model instance.
        
        Args:
            instance: Model instance to update
            update_data: Update data
            
        Returns:
            Updated model instance
        """
        pass
    
    @abstractmethod
    def delete(self, instance: Any) -> bool:
        """
        Delete model instance.
        
        Args:
            instance: Model instance to delete
            
        Returns:
            True if deleted successfully
        """
        pass


class IEventDAL(IDataAccessLayer):
    """
    Interface for event data access operations.
    
    Extends the base DAL interface with event-specific operations.
    """
    
    @abstractmethod
    def get_event_by_uuid(self, event_uuid: str) -> Optional[Any]:
        """
        Get event by UUID.
        
        Args:
            event_uuid: Event UUID
            
        Returns:
            Event instance or None
        """
        pass
    
    @abstractmethod
    def get_user_events_paginated(self, user_id: int, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get paginated list of user's events.
        
        Args:
            user_id: User ID
            filters: Query filters and pagination
            
        Returns:
            Dict with events and pagination info
        """
        pass


class IAlbumDAL(IDataAccessLayer):
    """
    Interface for album data access operations.
    
    Extends the base DAL interface with album-specific operations.
    """
    
    @abstractmethod
    def get_album_by_id(self, album_id: int) -> Optional[Any]:
        """
        Get album by ID.
        
        Args:
            album_id: Album ID
            
        Returns:
            Album instance or None
        """
        pass
    
    @abstractmethod
    def get_all_event_albums(self, event_id: int) -> List[Any]:
        """
        Get all albums for an event.
        
        Args:
            event_id: Event ID
            
        Returns:
            List of album instances
        """
        pass