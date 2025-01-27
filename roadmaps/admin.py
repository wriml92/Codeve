from django.contrib import admin
from .models import Course, UserCourse

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'description']

@admin.register(UserCourse)
class UserCourseAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'status', 'progress', 'started_at']
    list_filter = ['status']
    search_fields = ['user__username', 'course__name']
    raw_id_fields = ['user', 'course']
