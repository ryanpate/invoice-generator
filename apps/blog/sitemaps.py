"""
Sitemap configuration for blog app.
"""
from django.contrib.sitemaps import Sitemap
from .models import BlogPost


class BlogPostSitemap(Sitemap):
    """Sitemap for published blog posts."""
    changefreq = 'weekly'
    priority = 0.7
    protocol = 'https'

    def items(self):
        return BlogPost.objects.filter(status='published')

    def lastmod(self, item):
        return item.updated_at

    def location(self, item):
        return f'/blog/{item.slug}/'
