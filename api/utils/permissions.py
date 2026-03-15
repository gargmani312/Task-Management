from rest_framework import permissions
from user.models import Project, Task


class IsAdminOrManager(permissions.BasePermission):
    """Allows access only to admins or managers."""
    def hasattr_role(self, user):
        return user.is_authenticated and user.role in ['admin', 'manager']

    def has_permission(self, request, view):
        return self.hasattr_role(request.user)

class IsProjectCreator(permissions.BasePermission):
    """Allows access only to the user who created the project."""
    def has_object_permission(self, request, view, obj):
        return obj.created_by == request.user

class IsProjectMember(permissions.BasePermission):
    """Allows access if the user is a member of the project."""
    def has_permission(self, request, view):
        # Handle nested routes where project_id is in the URL
        project_id = view.kwargs.get('project_id')
        if project_id:
            return Project.objects.filter(id=project_id, members=request.user).exists()
        return True

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Project):
            return obj.members.filter(id=request.user.id).exists()
        elif hasattr(obj, 'project'):
            return obj.project.members.filter(id=request.user.id).exists()
        return False

class IsTaskAssigneeOrCreator(permissions.BasePermission):
    """Allows task updates by the assigned user or task creator."""
    def has_object_permission(self, request, view, obj):
        return request.user == obj.assigned_to or request.user == obj.created_by
    
    
    