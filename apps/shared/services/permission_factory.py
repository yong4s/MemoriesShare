"""
Permission Service Factory

Provides a centralized way to create and manage permission validators,
eliminating the need for direct service instantiation and reducing coupling.
"""

import logging
from typing import Optional, Type

from apps.shared.interfaces.permission_interface import IPermissionValidator, SimplePermissionValidator

logger = logging.getLogger(__name__)


class PermissionServiceFactory:
    """
    Factory for creating permission validators with proper dependency injection.
    
    This factory helps manage service lifecycles and provides different 
    permission validator implementations based on context and requirements.
    """

    _instance = None
    _validators = {}

    def __new__(cls):
        """Singleton pattern for global factory instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize factory with default configurations."""
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._default_validator_class = SimplePermissionValidator
            self._advanced_validator_class = None

    def register_advanced_validator(self, validator_class: Type[IPermissionValidator]) -> None:
        """
        Register an advanced permission validator class.
        
        This allows the factory to use a more sophisticated validator
        (like EventPermissionService) when available, while falling back
        to the simple implementation when needed.
        
        Args:
            validator_class: Class that implements IPermissionValidator
        """
        if not issubclass(validator_class, IPermissionValidator):
            raise ValueError("Validator class must implement IPermissionValidator interface")
        
        self._advanced_validator_class = validator_class
        logger.info(f"Registered advanced permission validator: {validator_class.__name__}")

    def create_permission_validator(
        self, 
        use_advanced: bool = True,
        dal=None,
        **kwargs
    ) -> IPermissionValidator:
        """
        Create appropriate permission validator instance.
        
        Args:
            use_advanced: Whether to use advanced validator if available
            dal: Optional DAL instance for advanced validators
            **kwargs: Additional arguments for validator initialization
            
        Returns:
            IPermissionValidator instance
        """
        try:
            if use_advanced and self._advanced_validator_class:
                # Try to create advanced validator with proper dependencies
                if dal is not None:
                    return self._advanced_validator_class(dal=dal, **kwargs)
                else:
                    return self._advanced_validator_class(**kwargs)
            else:
                # Fall back to simple validator
                return self._default_validator_class()
                
        except Exception as e:
            logger.warning(
                f"Failed to create advanced permission validator: {e}. "
                f"Falling back to simple validator."
            )
            return self._default_validator_class()

    def get_cached_validator(self, key: str, **create_kwargs) -> IPermissionValidator:
        """
        Get cached permission validator or create new one.
        
        This helps avoid creating multiple validator instances for the same context,
        improving performance and maintaining consistency.
        
        Args:
            key: Cache key for the validator
            **create_kwargs: Arguments for validator creation
            
        Returns:
            Cached or newly created IPermissionValidator instance
        """
        if key not in self._validators:
            self._validators[key] = self.create_permission_validator(**create_kwargs)
        
        return self._validators[key]

    def clear_cache(self) -> None:
        """Clear all cached validators."""
        self._validators.clear()
        logger.debug("Cleared permission validator cache")

    def get_album_permission_validator(self, dal=None) -> IPermissionValidator:
        """
        Get permission validator optimized for album operations.
        
        Args:
            dal: Optional DAL instance
            
        Returns:
            IPermissionValidator suitable for album operations
        """
        cache_key = f"album_validator_{id(dal) if dal else 'default'}"
        return self.get_cached_validator(
            cache_key,
            use_advanced=True,
            dal=dal
        )

    def get_event_permission_validator(self, dal=None) -> IPermissionValidator:
        """
        Get permission validator optimized for event operations.
        
        Args:
            dal: Optional DAL instance
            
        Returns:
            IPermissionValidator suitable for event operations
        """
        cache_key = f"event_validator_{id(dal) if dal else 'default'}"
        return self.get_cached_validator(
            cache_key,
            use_advanced=True,
            dal=dal
        )

    def get_simple_validator(self) -> IPermissionValidator:
        """
        Get simple permission validator for basic operations.
        
        Returns:
            SimplePermissionValidator instance
        """
        return self.get_cached_validator(
            "simple_validator",
            use_advanced=False
        )


# Global factory instance
permission_factory = PermissionServiceFactory()


def get_permission_validator(
    context: str = "default", 
    dal=None, 
    use_advanced: bool = True
) -> IPermissionValidator:
    """
    Convenient function to get permission validator for specific context.
    
    Args:
        context: Context for permission validation (album, event, default)
        dal: Optional DAL instance
        use_advanced: Whether to use advanced validator
        
    Returns:
        IPermissionValidator instance
    """
    if context == "album":
        return permission_factory.get_album_permission_validator(dal)
    elif context == "event":
        return permission_factory.get_event_permission_validator(dal)
    else:
        return permission_factory.create_permission_validator(use_advanced=use_advanced, dal=dal)


def register_permission_service(validator_class: Type[IPermissionValidator]) -> None:
    """
    Register advanced permission service for the factory.
    
    This should be called during application startup to register
    the full EventPermissionService implementation.
    
    Args:
        validator_class: Permission validator class to register
    """
    permission_factory.register_advanced_validator(validator_class)