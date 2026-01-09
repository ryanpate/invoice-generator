"""
URL patterns for blog app.
"""
from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    path('blog/', views.BlogListView.as_view(), name='list'),
    path('blog/category/<slug:slug>/', views.BlogCategoryView.as_view(), name='category'),
    path('blog/<slug:slug>/', views.BlogDetailView.as_view(), name='detail'),
]
