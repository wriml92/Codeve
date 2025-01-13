"""
URL configuration for Codeve project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render
from django.conf import settings
from django.conf.urls.static import static

def main_view(request):
    return render(request, 'base/main.html')

def main2_view(request):
    return render(request, 'base/main2.html')

urlpatterns = [
    path('', main_view, name='main'),
    path('practice/', main2_view, name='main2'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('api/courses/', include('courses.urls')),
    path('', include('social_django.urls', namespace='social')),
    path('api/communities/', include('communities.urls')), #커뮤니티 패스 추가
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
