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
from django.shortcuts import render, redirect
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from accounts.forms import CustomPasswordResetForm


def main_view(request):
    return render(request, 'base/main.html')


def practice_redirect(request):
    return redirect('courses:practice')


urlpatterns = [
    path('', main_view, name='main'),
    path('practice/', practice_redirect, name='practice'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('courses/', include('courses.urls')),
    path('api/communities/', include('communities.urls')),
    path('', include('chatbots.urls')),
    path('api/roadmaps/', include('roadmaps.urls')),
    path('accounts/password/reset/',
         auth_views.PasswordResetView.as_view(),
         name='password_reset'),
]
