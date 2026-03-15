import uuid
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from user.models import Project, Task, Comment, User
from api.serializers.serializer import ProjectSerializer, TaskSerializer, CommentSerializer
from api.utils.permissions import IsAdminOrManager, IsProjectCreator, IsProjectMember, IsTaskAssigneeOrCreator
from api.utils.pagination import StandardResultsSetPagination
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.core.cache import cache
from .models import ProjectReport
from api.serializers.serializer import ProjectReportSerializer
from .tasks import bulk_import_tasks


class ProjectListCreateView(generics.ListCreateAPIView):
    serializer_class = ProjectSerializer
    pagination_class = StandardResultsSetPagination

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsAdminOrManager()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return Project.objects.filter(members=self.request.user).select_related('created_by').prefetch_related('members')

    def perform_create(self, serializer):

        project = serializer.save(created_by=self.request.user)
        project.members.add(self.request.user)

class ProjectDetailUpdateView(generics.UpdateAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, IsProjectCreator]

class ProjectAddMemberView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk, *args, **kwargs):

        project = get_object_or_404(Project, pk=pk)
        
        is_creator = project.created_by == request.user
        is_manager = request.user.role in ['admin', 'manager'] and project.members.filter(id=request.user.id).exists()
        
        if not (is_creator or is_manager):
            raise PermissionDenied("Only the project creator or a project manager can add members.")

        user_id = request.data.get('user_id')
        user_to_add = get_object_or_404(User, pk=user_id)
        project.members.add(user_to_add)
        
        return Response({"message": f"User {user_to_add.username} added to project."}, status=status.HTTP_200_OK)


class ProjectTaskListCreateView(generics.ListCreateAPIView):
    serializer_class = TaskSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated, IsProjectMember]

    def get_queryset(self):
        project_id = self.kwargs.get('project_id')
        queryset = Task.objects.filter(project_id=project_id).select_related('created_by', 'assigned_to', 'project')
        
        status_param = self.request.query_params.get('status')
        priority = self.request.query_params.get('priority')
        assigned_to = self.request.query_params.get('assigned_to')

        if status_param: queryset = queryset.filter(status=status_param)
        if priority: queryset = queryset.filter(priority=priority)
        if assigned_to: queryset = queryset.filter(assigned_to_id=assigned_to)

        return queryset

    def perform_create(self, serializer):
        project = get_object_or_404(Project, pk=self.kwargs.get('project_id'))
        serializer.save(created_by=self.request.user, project=project)

class TaskUpdateView(generics.UpdateAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated, IsTaskAssigneeOrCreator]

class MyTasksListView(generics.ListAPIView):
    serializer_class = TaskSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Task.objects.filter(assigned_to=self.request.user).select_related('created_by', 'project')


class TaskCommentListCreateView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated] 

    def get_queryset(self):
        task_id = self.kwargs.get('task_id')
        task = get_object_or_404(Task, pk=task_id)
        
        if not task.project.members.filter(id=self.request.user.id).exists():
             raise PermissionDenied("You must be a project member to view comments.")
        
        return Comment.objects.filter(task_id=task_id).select_related('author').order_by('-created_at')

    def perform_create(self, serializer):

        task_id = self.kwargs.get('task_id')
        task = get_object_or_404(Task, pk=task_id)
        
        if not task.project.members.filter(id=self.request.user.id).exists():
            raise PermissionDenied("You must be a project member to add a comment.")

        serializer.save(author=self.request.user, task=task)

class ProjectReportListView(generics.ListAPIView):
    """Exposes past daily reports for a project."""
    serializer_class = ProjectReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        project_id = self.kwargs.get('project_id')
        return ProjectReport.objects.filter(project_id=project_id).order_by('-generated_at')

class BulkImportTasksView(APIView):
    """Accepts a JSON list of tasks and queues the import job."""
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        tasks_data = request.data
        if not isinstance(tasks_data, list):
            return Response({"error": "Expected a list of tasks."}, status=status.HTTP_400_BAD_REQUEST)
        
        job_id = str(uuid.uuid4())
        cache.set(f"job_{job_id}", {"status": "pending"}, timeout=3600)
        
        bulk_import_tasks.delay(job_id, project_id, request.user.id, tasks_data)
        
        return Response({"job_id": job_id}, status=status.HTTP_202_ACCEPTED)

class JobStatusView(APIView):
    """Checks the status of a queued background job using the cache."""
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        job_status = cache.get(f"job_{job_id}")
        if not job_status:
            return Response({"error": "Job not found or expired."}, status=status.HTTP_404_NOT_FOUND)
        return Response(job_status, status=status.HTTP_200_OK)
    
    
    