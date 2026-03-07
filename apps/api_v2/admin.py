from django.contrib import admin
from .models import DeviceToken


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'platform', 'is_active', 'created_at')
    list_filter = ('platform', 'is_active')
    search_fields = ('user__email', 'token')
