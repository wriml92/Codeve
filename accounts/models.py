from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class User(AbstractUser):
    email = models.EmailField(_('email address'), unique=True)
    google_id = models.CharField(max_length=255, null=True, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    profile_image = models.ImageField(
        upload_to='profile_images/', null=True, blank=True)
    is_email_verified = models.BooleanField(default=False)
    failed_login_attempts = models.IntegerField(default=0)
    last_login_attempt = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name='custom_user_set',
        related_query_name='custom_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name='custom_user_set',
        related_query_name='custom_user',
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def increment_login_attempts(self):
        self.failed_login_attempts += 1
        self.last_login_attempt = timezone.now()
        self.save()

    def reset_login_attempts(self):
        self.failed_login_attempts = 0
        self.save()

    def is_account_locked(self):
        if self.failed_login_attempts >= 5:
            if self.last_login_attempt:
                lock_duration = timezone.now() - self.last_login_attempt
                return lock_duration.seconds < 1800  # 30분 잠금
        return False


class SocialAccount(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='social_accounts')
    provider = models.CharField(max_length=30)  # 예: Google
    social_id = models.CharField(max_length=255)  # OAuth에서 제공받는 유저 ID
    access_token = models.CharField(max_length=255, null=True, blank=True)
    refresh_token = models.CharField(max_length=255, null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('provider', 'social_id')


class PasswordReset(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return not self.is_used and self.expires_at > timezone.now()
