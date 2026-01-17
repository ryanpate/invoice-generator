"""
URL patterns for blog app.
"""
from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.BlogListView.as_view(), name='list'),
    path('category/<slug:slug>/', views.BlogCategoryView.as_view(), name='category'),
    path('<slug:slug>/', views.BlogDetailView.as_view(), name='detail'),
]
