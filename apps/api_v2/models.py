from django.db import models
from django.conf import settings


class DeviceToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='device_tokens',
    )
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(
        max_length=10,
        choices=[('ios', 'iOS'), ('android', 'Android')],
        default='ios',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'token')

    def __str__(self):
        return f"{self.user.email} - {self.platform} ({self.token[:20]}...)"
