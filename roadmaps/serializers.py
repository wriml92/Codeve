from rest_framework import serializers
from .models import Course, UserCourse

class TopicStatusSerializer(serializers.Serializer):
    """토픽 완료 상태를 직렬화하는 시리얼라이저"""
    id = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    theory_completed = serializers.BooleanField()
    practice_completed = serializers.BooleanField()
    assignment_completed = serializers.BooleanField()
    reflection_completed = serializers.BooleanField()
    is_completed = serializers.BooleanField()

    def get_completion_status(self, topic_id, completed_topics):
        """토픽의 각 타입별 완료 상태를 반환"""
        return {
            'theory': f"{topic_id}_theory" in completed_topics,
            'practice': f"{topic_id}_practice" in completed_topics,
            'assignment': f"{topic_id}_assignment" in completed_topics,
            'reflection': f"{topic_id}_reflection" in completed_topics
        }

class CourseSerializer(serializers.ModelSerializer):
    """코스 정보를 직렬화하는 시리얼라이저"""
    topics = TopicStatusSerializer(many=True, read_only=True)
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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        
        if request and request.user.is_authenticated:
            user_course = UserCourse.objects.filter(
                user=request.user, 
                course=instance
            ).first()
            
            if user_course:
                completed_topics = user_course.get_completed_topics_list()
                for topic in data['topics']:
                    topic_id = str(topic['id'])
                    status = TopicStatusSerializer().get_completion_status(
                        topic_id, completed_topics
                    )
                    topic.update({
                        'theory_completed': status['theory'],
                        'practice_completed': status['practice'],
                        'assignment_completed': status['assignment'],
                        'reflection_completed': status['reflection'],
                        'is_completed': all(status.values())
                    })
                
                data['progress'] = user_course.progress
                data['is_enrolled'] = True
            else:
                data['progress'] = 0
                data['is_enrolled'] = False
        
        return data

class UserCourseSerializer(serializers.ModelSerializer):
    """사용자의 코스 수강 정보를 직렬화하는 시리얼라이저"""
    course_name = serializers.CharField(
        source='course.name',
        read_only=True
    )
    topic_status = serializers.SerializerMethodField()
    
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
            'topic_status',
            'started_at',
            'updated_at',
            'last_accessed_at'
        ]
        read_only_fields = [
            'user',
            'progress',
            'completed_topics',
            'topic_status'
        ] 

    def get_topic_status(self, obj):
        """현재 코스의 모든 토픽 완료 상태를 반환"""
        completed_topics = obj.get_completed_topics_list()
        topics = []
        
        for topic in obj.course.topics:
            topic_id = str(topic['id'])
            status = TopicStatusSerializer().get_completion_status(
                topic_id, completed_topics
            )
            topics.append({
                'id': topic_id,
                'name': topic['name'],
                'description': topic['description'],
                'theory_completed': status['theory'],
                'practice_completed': status['practice'],
                'assignment_completed': status['assignment'],
                'reflection_completed': status['reflection'],
                'is_completed': all(status.values())
            })
        
        return topics 