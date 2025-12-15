from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.events.models.invite_link_event import InviteEventLink

from .models import CustomUser


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer with user data"""

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = {
            "id": self.user.id,
            "email": self.user.email,
            "is_staff": self.user.is_staff,
            "is_active": self.user.is_active,
            "display_name": self.user.display_name,
            "is_guest": self.user.is_guest,
            "is_registered": self.user.is_registered,
            "date_joined": self.user.date_joined.isoformat(),
        }
        return data


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""

    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = CustomUser
        fields = ("email", "password", "password_confirm", "first_name", "last_name")

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email already exists.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError("Passwords do not match.")

        try:
            validate_password(attrs["password"])
        except ValidationError as e:
            raise serializers.ValidationError({"password": e.messages})

        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        user = CustomUser.objects.create_user(
            email=validated_data["email"],
            password=password,
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
        )
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile data"""

    class Meta:
        model = CustomUser
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "is_staff",
            "is_active",
            "display_name",
            "is_guest",
            "is_registered",
            "is_anonymous_guest",
            "guest_name",
            "date_joined",
        )
        read_only_fields = (
            "id",
            "date_joined",
            "is_guest",
            "is_registered",
            "is_anonymous_guest",
        )


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change"""

    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    new_password_confirm = serializers.CharField(required=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError("New passwords do not match.")

        try:
            validate_password(attrs["new_password"])
        except ValidationError as e:
            raise serializers.ValidationError({"new_password": e.messages})

        return attrs


class UserLoginSerializer(serializers.Serializer):
    """Serializer for session-based login"""

    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        if email and password:
            user = authenticate(
                request=self.context.get("request"), username=email, password=password
            )
            if not user:
                raise serializers.ValidationError("Invalid email or password.")
            if not user.is_active:
                raise serializers.ValidationError("User account is disabled.")
            attrs["user"] = user
            return attrs
        else:
            raise serializers.ValidationError("Must include email and password.")


class AnonymousGuestSerializer(serializers.Serializer):
    """Serializer for anonymous guest authentication"""

    invite_token = serializers.CharField(max_length=64)
    guest_name = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate_invite_token(self, value):
        try:
            invite = InviteEventLink.objects.get(invite_token=value)
            if not invite.is_active:
                raise serializers.ValidationError("Invalid or expired invite token.")
        except InviteEventLink.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired invite token.")
        return value


class PasswordlessRequestSerializer(serializers.Serializer):
    """Serializer for requesting passwordless verification code"""
    
    email = serializers.EmailField()

    def validate_email(self, value):
        """Validate email format"""
        return value.lower().strip()


class PasswordlessVerifySerializer(serializers.Serializer):
    """Serializer for verifying passwordless code"""
    
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)

    def validate_email(self, value):
        """Validate email format"""
        return value.lower().strip()

    def validate_code(self, value):
        """Validate code is 6 digits"""
        if not value.isdigit():
            raise serializers.ValidationError("Code must be 6 digits")
        return value


class SetPasswordSerializer(serializers.Serializer):
    """Serializer for setting password for passwordless users"""
    
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """Validate passwords match"""
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError("Passwords do not match")
        
        # Django password validation
        from django.contrib.auth.password_validation import validate_password
        validate_password(attrs["password"])
        
        return attrs
