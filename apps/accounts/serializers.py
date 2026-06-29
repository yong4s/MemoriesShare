from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import CustomUser


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer with user data"""

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = {
            'id': self.user.id,
            'email': self.user.email,
            'is_staff': self.user.is_staff,
            'is_active': self.user.is_active,
            'display_name': self.user.display_name,
            'is_guest': self.user.is_guest,
            'is_registered': self.user.is_registered,
            'date_joined': self.user.date_joined.isoformat(),
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
        fields = ('email', 'password', 'password_confirm', 'first_name', 'last_name')

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            msg = 'User with this email already exists.'
            raise serializers.ValidationError(msg)
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            msg = 'Passwords do not match.'
            raise serializers.ValidationError(msg)

        try:
            validate_password(attrs['password'])
        except ValidationError as e:
            raise serializers.ValidationError({'password': e.messages})

        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        return CustomUser.objects.create_user(
            email=validated_data['email'],
            password=password,
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
        )


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile data"""

    preferred_login_method = serializers.ChoiceField(
        choices=CustomUser.LoginMethod.choices,
        required=False,
    )
    has_password = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            'id',
            'email',
            'first_name',
            'last_name',
            'is_staff',
            'is_active',
            'display_name',
            'is_guest',
            'is_registered',
            'is_anonymous_guest',
            'guest_name',
            'date_joined',
            'preferred_login_method',
            'has_password',
            'password_changed_at',
        )
        read_only_fields = (
            'id',
            'date_joined',
            'is_guest',
            'is_registered',
            'is_anonymous_guest',
            'has_password',
            'password_changed_at',
        )

    def get_has_password(self, obj: CustomUser) -> bool:
        return obj.has_usable_password()

    def validate_preferred_login_method(self, value: str) -> str:
        user = getattr(self.instance, 'pk', None) and self.instance
        if value == CustomUser.LoginMethod.PASSWORD and user and not user.has_usable_password():
            msg = 'Cannot prefer password login without a password set'
            raise serializers.ValidationError(msg)
        return value


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change"""

    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    new_password_confirm = serializers.CharField(required=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            msg = 'Old password is incorrect.'
            raise serializers.ValidationError(msg)
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            msg = 'New passwords do not match.'
            raise serializers.ValidationError(msg)

        try:
            validate_password(attrs['new_password'])
        except ValidationError as e:
            raise serializers.ValidationError({'new_password': e.messages})

        return attrs


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
            msg = 'Code must be 6 digits'
            raise serializers.ValidationError(msg)
        return value


class SetPasswordSerializer(serializers.Serializer):
    """Serializer for setting password for passwordless users"""

    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """Validate passwords match"""
        if attrs['password'] != attrs['password_confirm']:
            msg = 'Passwords do not match'
            raise serializers.ValidationError(msg)

        try:
            validate_password(attrs['password'])
        except ValidationError as exc:
            raise serializers.ValidationError({'password': exc.messages})

        return attrs


class LoginMethodsRequestSerializer(serializers.Serializer):
    """Request body for login-methods discovery endpoint"""

    email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        return value.lower().strip()


class LoginMethodsResponseSerializer(serializers.Serializer):
    """Response body for login-methods discovery endpoint"""

    password = serializers.BooleanField()
    passwordless = serializers.BooleanField()
    preferred = serializers.ChoiceField(choices=CustomUser.LoginMethod.choices)
