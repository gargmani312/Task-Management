import time
from celery import shared_task
from django.core.cache import cache
from django.utils.timezone import now
from django.contrib.auth import get_user_model
from user.models import Project, Task
from api.models import ProjectReport

User = get_user_model()

@shared_task
def send_task_assignment_email(assignee_name, task_title, project_name, due_date):
    """Simulates sending an assignment email with network delay."""
    time.sleep(2)
    print("=" * 40)
    print("EMAIL NOTIFICATION")
    print(f"To: {assignee_name}")
    print(f"Task: '{task_title}' in Project: '{project_name}'")
    print(f"Due Date: {due_date}")
    print("=" * 40)

@shared_task
def generate_daily_project_report():
    """Calculates active project statistics and saves to ProjectReport."""
    active_projects = Project.objects.filter(is_active=True)
    for project in active_projects:
        total_tasks = project.tasks.count()
        status_counts = {
            'todo': project.tasks.filter(status='todo').count(),
            'in_progress': project.tasks.filter(status='in_progress').count(),
            'review': project.tasks.filter(status='review').count(),
            'done': project.tasks.filter(status='done').count(),
        }
        overdue_tasks = project.tasks.filter(
            due_date__lt=now(), 
            status__in=['todo', 'in_progress', 'review']
        ).count()
        
        report_data = {
            "total_tasks": total_tasks,
            "tasks_by_status": status_counts,
            "overdue_tasks": overdue_tasks
        }
        
        ProjectReport.objects.create(project=project, report_data=report_data)

@shared_task
def bulk_import_tasks(job_id, project_id, user_id, tasks_data):
    """Processes a bulk list of tasks and updates cache status."""
    cache.set(f"job_{job_id}", {"status": "in_progress"}, timeout=3600)
    
    try:
        project = Project.objects.get(id=project_id)
        user = User.objects.get(id=user_id)
        
        tasks_to_create = [
            Task(
                project=project,
                created_by=user,
                title=item.get('title'),
                description=item.get('description', ''),
                priority=item.get('priority', 'medium'),
                due_date=item.get('due_date')
            ) for item in tasks_data
        ]
        
        Task.objects.bulk_create(tasks_to_create)
        cache.set(f"job_{job_id}", {"status": "completed", "imported_count": len(tasks_to_create)}, timeout=3600)
    except Exception as e:
        cache.set(f"job_{job_id}", {"status": "failed", "error": str(e)}, timeout=3600)
        
        
        
        