"""
Views for blog app.
"""
from django.views.generic import ListView, DetailView
from django.db.models import Q, F

from .models import BlogPost, BlogCategory


class BlogListView(ListView):
    """List all published blog posts."""
    model = BlogPost
    template_name = 'blog/list.html'
    context_object_name = 'posts'
    paginate_by = 10

    def get_queryset(self):
        queryset = BlogPost.objects.filter(
            status='published'
        ).select_related('author', 'category')

        # Search filter
        search = self.request.GET.get('q')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(content__icontains=search) |
                Q(excerpt__icontains=search)
            )

        # Category filter
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)

        return queryset.order_by('-published_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = BlogCategory.objects.all()
        context['search_query'] = self.request.GET.get('q', '')
        context['current_category'] = self.request.GET.get('category', '')
        return context


class BlogDetailView(DetailView):
    """View single blog post."""
    model = BlogPost
    template_name = 'blog/detail.html'
    context_object_name = 'post'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        return BlogPost.objects.filter(
            status='published'
        ).select_related('author', 'category')

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Increment view count
        BlogPost.objects.filter(pk=obj.pk).update(view_count=F('view_count') + 1)
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.object

        # Related posts (same category, excluding current)
        if post.category:
            context['related_posts'] = BlogPost.objects.filter(
                category=post.category,
                status='published'
            ).exclude(pk=post.pk).order_by('-published_date')[:3]
        else:
            context['related_posts'] = BlogPost.objects.filter(
                status='published'
            ).exclude(pk=post.pk).order_by('-published_date')[:3]

        return context


class BlogCategoryView(ListView):
    """List posts by category."""
    model = BlogPost
    template_name = 'blog/list.html'
    context_object_name = 'posts'
    paginate_by = 10

    def get_queryset(self):
        return BlogPost.objects.filter(
            status='published',
            category__slug=self.kwargs['slug']
        ).select_related('author', 'category').order_by('-published_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = BlogCategory.objects.all()
        context['current_category'] = self.kwargs['slug']
        context['category'] = BlogCategory.objects.filter(
            slug=self.kwargs['slug']
        ).first()
        return context
