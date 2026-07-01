from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication


class BaseEventAPIView(APIView):
    """
    Base view for event operations

    Provides only JWT authentication - no dependency injection.
    Use service mixins for DI to follow Interface Segregation Principle.
    """

    authentication_classes = (JWTAuthentication,)
