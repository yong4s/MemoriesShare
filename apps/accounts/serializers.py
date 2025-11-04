"""
Serializers for authentication
"""

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import CustomUser


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer that includes additional user data
    """

    def validate(self, attrs):
        data = super().validate(attrs)

        # Add custom user data to the response
        data['user'] = {
            'id': self.user.id,
            'email': self.user.email,
            'is_staff': self.user.is_staff,
            'is_active': self.user.is_active,
            'display_name': self.user.display_name,
            'is_anonymous_guest': self.user.is_anonymous_guest,
            'date_joined': self.user.date_joined.isoformat(),
        }

        return data


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration
    """

    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ('email', 'password', 'password_confirm')

    def validate_email(self, value):
        """Validate email uniqueness"""
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError('User with this email already exists.')
        return value

    def validate(self, attrs):
        """Validate password confirmation"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError('Passwords do not match.')

        # Validate password strength
        try:
            validate_password(attrs['password'])
        except ValidationError as e:
            raise serializers.ValidationError({'password': e.messages})

        return attrs

    def create(self, validated_data):
        """Create user with encrypted password"""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')

        user = CustomUser.objects.create_user(email=validated_data['email'], password=password)
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile data
    """

    class Meta:
        model = CustomUser
        fields = (
            'id',
            'email',
            'is_staff',
            'is_active',
            'display_name',
            'is_anonymous_guest',
            'guest_name',
            'date_joined',
        )
        read_only_fields = ('id', 'date_joined', 'is_anonymous_guest')


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for password change
    """

    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    new_password_confirm = serializers.CharField(required=True)

    def validate_old_password(self, value):
        """Validate old password"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Old password is incorrect.')
        return value

    def validate(self, attrs):
        """Validate new password confirmation"""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError('New passwords do not match.')

        # Validate password strength
        try:
            validate_password(attrs['new_password'])
        except ValidationError as e:
            raise serializers.ValidationError({'new_password': e.messages})

        return attrs


class UserLoginSerializer(serializers.Serializer):
    """
    Serializer for user login (alternative to JWT)
    """

    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(request=self.context.get('request'), username=email, password=password)

            if not user:
                raise serializers.ValidationError('Invalid email or password.')

            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')

            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include email and password.')


class AnonymousGuestSerializer(serializers.Serializer):
    """
    Serializer for creating anonymous guest users via invite token
    """

    invite_token = serializers.CharField(max_length=64)
    guest_name = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate_invite_token(self, value):
        """Validate invite token"""
        from .models import EventInvite

        invite = EventInvite.objects.get_valid_invite(value)
        if not invite:
            raise serializers.ValidationError('Invalid or expired invite token.')

        return value

    def create(self, validated_data):
        """Create anonymous guest user"""
        invite_token = validated_data['invite_token']
        guest_name = validated_data.get('guest_name')

        user = CustomUser.create_anonymous_guest(invite_token=invite_token, guest_name=guest_name)

        # Mark invite as used
        from .models import EventInvite

        invite = EventInvite.objects.get_valid_invite(invite_token)
        if invite:
            invite.use_invite(guest_user=user)

        return user
