"""
Company profile views for API v2.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.companies.models import Company
from apps.api_v2.serializers.company import CompanyV2Serializer


def _get_or_create_company(user):
    """Return the company for this user, creating a default one if needed."""
    company = user.get_company()
    if company is None:
        company, _ = Company.objects.get_or_create(
            user=user,
            defaults={'name': f"{user.username}'s Company"},
        )
    return company


@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def company_detail(request):
    """
    GET  /api/v2/company/    — retrieve company profile
    PUT  /api/v2/company/    — full update of company profile
    PATCH /api/v2/company/   — partial update of company profile
    """
    company = _get_or_create_company(request.user)

    if request.method == 'GET':
        serializer = CompanyV2Serializer(company, context={'request': request})
        return Response(serializer.data)

    partial = request.method == 'PATCH'
    serializer = CompanyV2Serializer(
        company,
        data=request.data,
        partial=partial,
        context={'request': request},
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_logo(request):
    """
    POST /api/v2/company/logo/

    Accepts multipart/form-data with a 'logo' file field.
    Replaces the existing logo (old file is deleted by the Company.save() hook).
    """
    if 'logo' not in request.FILES:
        return Response(
            {'error': 'No logo file provided. Send a multipart/form-data request with a "logo" field.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    company = _get_or_create_company(request.user)
    company.logo = request.FILES['logo']
    company.save(update_fields=['logo'])

    serializer = CompanyV2Serializer(company, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_logo(request):
    """
    DELETE /api/v2/company/logo/

    Removes the company logo and deletes the underlying file.
    """
    company = _get_or_create_company(request.user)

    if company.logo:
        company.logo.delete(save=False)
        company.logo = None
        company.save(update_fields=['logo'])

    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_signature(request):
    """
    POST /api/v2/company/signature/

    Accepts multipart/form-data with a 'signature' file field.
    Replaces the existing signature (old file is deleted by the Company.save() hook).
    """
    if 'signature' not in request.FILES:
        return Response(
            {'error': 'No signature file provided. Send a multipart/form-data request with a "signature" field.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    company = _get_or_create_company(request.user)
    company.signature = request.FILES['signature']
    company.save(update_fields=['signature'])

    serializer = CompanyV2Serializer(company, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_signature(request):
    """
    DELETE /api/v2/company/signature/

    Removes the company signature and deletes the underlying file.
    """
    company = _get_or_create_company(request.user)

    if company.signature:
        company.signature.delete(save=False)
        company.signature = None
        company.save(update_fields=['signature'])

    return Response(status=status.HTTP_204_NO_CONTENT)
