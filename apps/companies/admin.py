"""
Admin configuration for companies app.
"""
from django.contrib import admin
from .models import Company, TeamMember, TeamInvitation


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'email', 'default_currency', 'team_member_count', 'created_at']
    list_filter = ['default_currency', 'country']
    search_fields = ['name', 'owner__email', 'email']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['user', 'owner']

    def team_member_count(self, obj):
        """Display team member count."""
        return obj.get_team_member_count()
    team_member_count.short_description = 'Team Members'


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ['user', 'company', 'role', 'invited_by', 'joined_at']
    list_filter = ['role', 'joined_at']
    search_fields = ['user__email', 'company__name']
    raw_id_fields = ['user', 'company', 'invited_by']
    readonly_fields = ['joined_at']

    actions = ['make_admin', 'make_member']

    @admin.action(description='Make selected members Admins')
    def make_admin(self, request, queryset):
        queryset.update(role='admin')

    @admin.action(description='Make selected members regular Members')
    def make_member(self, request, queryset):
        queryset.update(role='member')


@admin.register(TeamInvitation)
class TeamInvitationAdmin(admin.ModelAdmin):
    list_display = ['email', 'company', 'role', 'invited_by', 'accepted', 'is_expired_display', 'created_at', 'expires_at']
    list_filter = ['role', 'accepted', 'created_at']
    search_fields = ['email', 'company__name', 'invited_by__email']
    raw_id_fields = ['company', 'invited_by']
    readonly_fields = ['token', 'created_at']

    def is_expired_display(self, obj):
        """Display expiration status."""
        return obj.is_expired
    is_expired_display.boolean = True
    is_expired_display.short_description = 'Expired'

    actions = ['mark_accepted', 'cancel_invitations']

    @admin.action(description='Mark selected invitations as accepted')
    def mark_accepted(self, request, queryset):
        queryset.update(accepted=True)

    @admin.action(description='Cancel selected invitations (delete)')
    def cancel_invitations(self, request, queryset):
        queryset.delete()
