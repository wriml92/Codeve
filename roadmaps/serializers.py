from rest_framework import serializers
from .models import Course, UserCourse

class CourseSerializer(serializers.ModelSerializer):
    """코스 정보를 직렬화하는 시리얼라이저"""
    progress = serializers.FloatField(read_only=True)
    is_enrolled = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Course
        fields = [
            'id', 
            'name', 
            'description',
            'category',
            'topics', 
            'estimated_hours',
            'is_active',
            'order',
            'progress',
            'is_enrolled'
        ]

class UserCourseSerializer(serializers.ModelSerializer):
    """사용자의 코스 수강 정보를 직렬화하는 시리얼라이저"""
    course_name = serializers.CharField(
        source='course.name',
        read_only=True
    )
    
    class Meta:
        model = UserCourse
        fields = [
            'id',
            'user',
            'course',
            'course_name',
            'status',
            'progress',
            'completed_topics',
            'started_at',
            'updated_at',
            'last_accessed_at'
        ]
        read_only_fields = [
            'user',
            'progress',
            'completed_topics'
        ] 