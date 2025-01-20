from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Roadmap(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    difficulty = models.CharField(
        max_length=20,
        choices=[
            ('beginner', '입문'),
            ('intermediate', '중급'),
            ('advanced', '고급')
        ]
    )
    estimated_hours = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class RoadmapStep(models.Model):
    roadmap = models.ForeignKey(Roadmap, on_delete=models.CASCADE, related_name='steps')
    title = models.CharField(max_length=200)
    description = models.TextField()
    order = models.IntegerField()
    estimated_hours = models.IntegerField()
    
    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.roadmap.title} - Step {self.order}: {self.title}"

class UserRoadmap(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    roadmap = models.ForeignKey(Roadmap, on_delete=models.CASCADE)
    current_step = models.ForeignKey(RoadmapStep, on_delete=models.SET_NULL, null=True)
    progress = models.IntegerField(default=0)  # 진행률(%)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['user', 'roadmap']
