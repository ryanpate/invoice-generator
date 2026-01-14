"""
URL patterns for companies app.
"""
from django.urls import path
from . import views

app_name = 'companies'

urlpatterns = [
    path('company/', views.CompanySettingsView.as_view(), name='settings'),
    path('company/remove-logo/', views.remove_logo, name='remove_logo'),
    path('company/remove-signature/', views.remove_signature, name='remove_signature'),

    # Team management
    path('team/', views.TeamManagementView.as_view(), name='team'),
    path('team/invite/', views.InviteTeamMemberView.as_view(), name='team_invite'),
    path('team/member/<int:pk>/remove/', views.RemoveTeamMemberView.as_view(), name='team_remove'),
    path('team/invitation/<int:pk>/cancel/', views.CancelInvitationView.as_view(), name='team_cancel_invitation'),
]
