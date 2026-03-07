import jwt
import requests
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser
from apps.api_v2.serializers.auth import (
    RegisterSerializer,
    LoginSerializer,
    AppleSocialAuthSerializer,
    GoogleSocialAuthSerializer,
)


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': {
            'id': user.id,
            'email': user.email,
            'subscription_tier': user.subscription_tier,
        },
    }


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    return Response(get_tokens_for_user(user), status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.validated_data['user']
    return Response(get_tokens_for_user(user), status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def apple_social_auth_view(request):
    serializer = AppleSocialAuthSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    id_token = serializer.validated_data['id_token']

    try:
        apple_keys_url = 'https://appleid.apple.com/auth/keys'
        apple_keys = requests.get(apple_keys_url, timeout=10).json()
        header = jwt.get_unverified_header(id_token)
        key = None
        for k in apple_keys['keys']:
            if k['kid'] == header['kid']:
                key = jwt.algorithms.RSAAlgorithm.from_jwk(k)
                break
        if not key:
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)

        payload = jwt.decode(
            id_token,
            key,
            algorithms=['RS256'],
            audience=settings.APPLE_CLIENT_ID,
            issuer='https://appleid.apple.com',
        )
    except Exception:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)

    email = payload.get('email')
    if not email:
        return Response({'error': 'Email not provided'}, status=status.HTTP_400_BAD_REQUEST)

    user, created = CustomUser.objects.get_or_create(
        email=email,
        defaults={
            'username': email.split('@')[0],
            'first_name': serializer.validated_data.get('first_name', ''),
            'last_name': serializer.validated_data.get('last_name', ''),
        },
    )

    return Response(
        get_tokens_for_user(user),
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def google_social_auth_view(request):
    serializer = GoogleSocialAuthSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    id_token_str = serializer.validated_data['id_token']

    try:
        google_url = f'https://oauth2.googleapis.com/tokeninfo?id_token={id_token_str}'
        resp = requests.get(google_url, timeout=10)
        if resp.status_code != 200:
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)
        payload = resp.json()
    except Exception:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)

    email = payload.get('email')
    if not email:
        return Response({'error': 'Email not provided'}, status=status.HTTP_400_BAD_REQUEST)

    user, created = CustomUser.objects.get_or_create(
        email=email,
        defaults={
            'username': email.split('@')[0],
            'first_name': payload.get('given_name', ''),
            'last_name': payload.get('family_name', ''),
        },
    )

    return Response(
        get_tokens_for_user(user),
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(['DELETE'])
def delete_account_view(request):
    user = request.user
    user.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
