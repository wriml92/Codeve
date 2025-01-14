from django.urls import path
from . import views

app_name = 'communities'

urlpatterns = [
    path('posts/', views.posts_list_view, name='posts-list'),
    path('posts/<int:pk>/', views.post_detail_view, name='post-detail'),
    path('posts/create/', views.post_create_view, name='post-create'),
    path('posts/<int:pk>/edit/', views.post_edit_view, name='post-edit'),
    path('posts/<int:pk>/delete/', views.post_delete_view, name='post-delete'),
] 