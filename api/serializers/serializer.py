from rest_framework import serializers
from user.models import Project, Task, Comment, User
from user.serializers.serializer import UserSerializer, RegisterSerializer
from api.models import ProjectReport


class ProjectSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    members = UserSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = ('id', 'name', 'description', 'created_by', 'members', 'is_active', 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at')

class TaskSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    assigned_to = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False, allow_null=True)
    
    class Meta:
        model = Task
        fields = ('id', 'title', 'description', 'project', 'assigned_to', 'created_by', 'status', 'priority', 'due_date', 'created_at', 'updated_at')
        read_only_fields = ('project', 'created_at', 'updated_at')

class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ('id', 'task', 'author', 'content', 'created_at', 'updated_at')
        read_only_fields = ('task', 'created_at', 'updated_at')

class ProjectReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectReport
        fields = ('id', 'project', 'report_data', 'generated_at')
        
        
        