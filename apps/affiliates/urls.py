from django.urls import path
from . import views

app_name = 'affiliates'

urlpatterns = [
    path('', views.AffiliateDashboardView.as_view(), name='dashboard'),
    path('apply/', views.AffiliateApplyView.as_view(), name='apply'),
    path('commissions/', views.AffiliateCommissionsView.as_view(), name='commissions'),
    path('referrals/', views.AffiliateReferralsView.as_view(), name='referrals'),
    path('program/', views.AffiliateProgramView.as_view(), name='program'),
]
