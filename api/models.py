from django.db import models
from user.models import Project

class ProjectReport(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='reports')
    report_data = models.JSONField()
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report for {self.project.name} at {self.generated_at}"
    
    
    