"""
Models for blog app.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify


class BlogCategory(models.Model):
    """Category for organizing blog posts."""
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Blog Category'
        verbose_name_plural = 'Blog Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class BlogPost(models.Model):
    """Blog post for SEO content."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blog_posts'
    )
    category = models.ForeignKey(
        BlogCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posts'
    )
    excerpt = models.TextField(
        max_length=300,
        help_text='Brief summary for previews and meta description (max 300 chars)'
    )
    content = models.TextField(help_text='Full post content (HTML supported)')
    featured_image = models.ImageField(
        upload_to='blog/featured/%Y/%m/',
        blank=True,
        null=True,
        help_text='Recommended size: 1200x630px for social sharing'
    )
    meta_description = models.CharField(
        max_length=160,
        blank=True,
        help_text='SEO meta description (max 160 chars). Uses excerpt if blank.'
    )
    meta_keywords = models.CharField(
        max_length=255,
        blank=True,
        help_text='Comma-separated keywords for SEO'
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='draft'
    )
    published_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Leave blank to auto-set when published'
    )
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Blog Post'
        verbose_name_plural = 'Blog Posts'
        ordering = ['-published_date', '-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['status', 'published_date']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Auto-generate slug from title
        if not self.slug:
            self.slug = slugify(self.title)

        # Auto-set published_date when status changes to published
        if self.status == 'published' and not self.published_date:
            self.published_date = timezone.now()

        super().save(*args, **kwargs)

    def get_meta_description(self):
        """Return meta_description or excerpt as fallback."""
        return self.meta_description or self.excerpt[:160]

    def is_published(self):
        """Check if post is published."""
        return self.status == 'published'
