from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication


class BaseAPIView(APIView):
    """
    Unified base class for all API views in Media Flow project.

    Features:
    - JWT-only authentication
    - Service layer integration

    Note: Exception handling is centralized through middleware.
    """

    authentication_classes = (JWTAuthentication,)

    def get_service(self):
        """
        Subclasses must implement this to return appropriate service instance.

        Returns:
            Service instance for business logic operations

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement get_service()")
