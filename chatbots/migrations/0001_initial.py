# Generated by Django 5.1.4 on 2025-01-27 13:39

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CachedResponse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question_hash', models.CharField(max_length=64, unique=True)),
                ('question', models.TextField()),
                ('response', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField(help_text='사용자의 질문 내용')),
                ('response', models.TextField(help_text='AI의 응답 내용')),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='대화가 생성된 시간')),
                ('user', models.ForeignKey(help_text='대화를 나눈 사용자', on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': '대화 내용',
                'verbose_name_plural': '대화 내용들',
                'ordering': ['-created_at'],
            },
        ),
    ]
