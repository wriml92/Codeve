from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy

app_name = 'accounts'

urlpatterns = [
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('google/login/', views.GoogleLoginView.as_view(), name='google_login'),
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('password/change/', views.PasswordChangeView.as_view(), name='password_change'),
    path('my-page/', views.MyPageView.as_view(), name='my_page'),
    
    # 비밀번호 재설정 관련 URL 패턴
    path('password/reset/', 
        auth_views.PasswordResetView.as_view(
            template_name='accounts/password-reset.html',
            email_template_name='accounts/password_reset_email.html',
            subject_template_name='accounts/password_reset_subject.txt',
            success_url=reverse_lazy('accounts:password_reset_done')
        ),
        name='password_reset'),
    
    path('password/reset/done/',
        auth_views.PasswordResetDoneView.as_view( 
            template_name='accounts/password_reset_done.html'
        ),
        name='password_reset_done'),
    
    path('password/reset/confirm/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/password_reset_confirm.html',
            success_url=reverse_lazy('accounts:password_reset_complete')
        ),
        name='password_reset_confirm'),
    
    path('password/reset/complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='accounts/password_reset_complete.html'
        ),
        name='password_reset_complete'),
] 