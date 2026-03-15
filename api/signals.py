from django.db.models.signals import pre_save
from django.dispatch import receiver
from user.models import Task
from api.tasks import send_task_assignment_email
from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from user.models import Task, Comment

@receiver(pre_save, sender=Task)
def trigger_assignment_email(sender, instance, **kwargs):
    should_send = False

    if instance.pk:

        old_task = Task.objects.get(pk=instance.pk)
        if instance.assigned_to and old_task.assigned_to != instance.assigned_to:
            should_send = True
    else:

        if instance.assigned_to:
            should_send = True

    if should_send:
        send_task_assignment_email.delay(
            assignee_name=instance.assigned_to.username,
            task_title=instance.title,
            project_name=instance.project.name,
            due_date=str(instance.due_date) if instance.due_date else "None"
        )


channel_layer = get_channel_layer()


@receiver(post_save, sender=Task)
def broadcast_task_changes(sender, instance, created, **kwargs):
    """Triggers task_created and task_updated events."""
    group_name = f"project_{instance.project.id}"
    
    if created:
        event_type = "task_created"
        data = {
            "event": event_type, 
            "task_id": instance.id, 
            "title": instance.title,
            "status": instance.status
        }
        async_to_sync(channel_layer.group_send)(
            group_name, {"type": "task_created", "data": data}
        )
    else:
        event_type = "task_updated"
        data = {
            "event": event_type, 
            "task_id": instance.id, 
            "status": instance.status
        }
        async_to_sync(channel_layer.group_send)(
            group_name, {"type": "task_updated", "data": data}
        )

@receiver(post_save, sender=Comment)
def broadcast_new_comment(sender, instance, created, **kwargs):
    """Triggers new_comment events."""
    if created:
        group_name = f"project_{instance.task.project.id}"
        data = {
            "event": "new_comment", 
            "task_id": instance.task.id, 
            "comment_id": instance.id, 
            "author": instance.author.username,
            "content": instance.content
        }
        async_to_sync(channel_layer.group_send)(
            group_name, {"type": "new_comment", "data": data}
        )
        