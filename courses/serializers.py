from rest_framework import serializers
from .models import Course, Lesson, Quiz, PracticeExercise, UserCourse


class QuizSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = '__all__'


class PracticeExerciseSerializer(serializers.ModelSerializer):
    class Meta:
        model = PracticeExercise
        fields = '__all__'


class LessonSerializer(serializers.ModelSerializer):
    quizzes = QuizSerializer(many=True, read_only=True)
    exercises = PracticeExerciseSerializer(many=True, read_only=True)

    class Meta:
        model = Lesson
        fields = '__all__'


class CourseSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)
    enrolled_students_count = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = '__all__'

    def get_enrolled_students_count(self, obj):
        return obj.user_courses.count()


class UserCourseSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    course_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = UserCourse
        fields = '__all__'
        read_only_fields = ('user', 'progress_percentage', 'enrolled_at',
                            'completed_at', 'last_accessed_at')

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
