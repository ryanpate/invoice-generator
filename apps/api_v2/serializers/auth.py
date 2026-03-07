from rest_framework import serializers
from django.contrib.auth import authenticate
from apps.accounts.models import CustomUser


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value.lower()

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        return data

    def create(self, validated_data):
        email = validated_data['email']
        user = CustomUser.objects.create_user(
            username=email.split('@')[0],
            email=email,
            password=validated_data['password'],
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError('Invalid email or password.')
        if not user.is_active:
            raise serializers.ValidationError('Account is disabled.')
        data['user'] = user
        return data


class AppleSocialAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField()
    first_name = serializers.CharField(required=False, default='')
    last_name = serializers.CharField(required=False, default='')


class GoogleSocialAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField()
