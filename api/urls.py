from django.urls import path
from . import views

urlpatterns = [
    # Projects
    path('projects/', views.ProjectListCreateView.as_view(), name='project-list-create'),
    path('projects/<int:pk>/', views.ProjectDetailUpdateView.as_view(), name='project-detail-update'),
    path('projects/<int:pk>/add-member/', views.ProjectAddMemberView.as_view(), name='project-add-member'),

    # Tasks
    path('projects/<int:project_id>/tasks/', views.ProjectTaskListCreateView.as_view(), name='project-task-list-create'),
    path('tasks/<int:pk>/', views.TaskUpdateView.as_view(), name='task-update'),
    path('tasks/my-tasks/', views.MyTasksListView.as_view(), name='my-tasks-list'),

    # Comments
    path('tasks/<int:task_id>/comments/', views.TaskCommentListCreateView.as_view(), name='task-comment-list-create'),
    
    # 
    path('projects/<int:project_id>/reports/', views.ProjectReportListView.as_view(), name='project-reports'),
    path('projects/<int:project_id>/import-tasks/', views.BulkImportTasksView.as_view(), name='bulk-import-tasks'),
    path('jobs/<str:job_id>/status/', views.JobStatusView.as_view(), name='job-status'),
]


