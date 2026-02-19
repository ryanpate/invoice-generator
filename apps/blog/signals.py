import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.blog.models import BlogPost
from apps.invoices.services.indexnow import notify_indexnow

logger = logging.getLogger(__name__)


@receiver(post_save, sender=BlogPost)
def ping_indexnow_on_blog_publish(sender, instance, created, **kwargs):
    """Notify Bing/IndexNow when a blog post is published."""
    if instance.status == 'published':
        url = f"https://www.invoicekits.com/blog/{instance.slug}/"
        try:
            notify_indexnow(url)
        except Exception:
            logger.exception("Failed to notify IndexNow for %s", url)
