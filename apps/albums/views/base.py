from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication


class BaseAlbumAPIView(APIView):
    """
    Base view for album operations.

    Provides only JWT authentication - no dependency injection.
    Use _create_service() in child views for DI.
    """

    authentication_classes = (JWTAuthentication,)
