from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.test import override_settings
from django.contrib.auth import get_user_model
from user.models import Project, Task

User = get_user_model()

class TaskManagementAPITests(APITestCase):
    def setUp(self):
        # Create users with different roles
        self.admin_user = User.objects.create_user(username='admin', password='password123', role='admin')
        self.member_user = User.objects.create_user(username='member', password='password123', role='member')
        self.non_member_user = User.objects.create_user(username='outsider', password='password123', role='member')

        # Create a project and add the member_user to it
        self.project = Project.objects.create(name='Test Project', created_by=self.admin_user)
        self.project.members.add(self.admin_user, self.member_user)

    # --- Auth Tests [cite: 79] ---

    def test_01_user_register(self):
        """Test user registration returns a token[cite: 80]."""
        url = reverse('register')
        data = {'username': 'newuser', 'password': 'newpassword123', 'email': 'new@test.com'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)

    def test_02_user_login(self):
        """Test user login returns a token[cite: 80]."""
        url = reverse('login')
        data = {'username': 'member', 'password': 'password123'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_03_access_protected_route_without_token(self):
        """Test accessing a protected route without authentication fails[cite: 80]."""
        url = reverse('project-list-create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- Permission Tests [cite: 81] ---

    def test_04_member_cannot_create_projects(self):
        """Test that a user with the 'member' role cannot create a project."""
        self.client.force_authenticate(user=self.member_user)
        url = reverse('project-list-create')
        data = {'name': 'Member Project', 'description': 'Should fail'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_05_admin_can_create_projects(self):
        """Test that a user with the 'admin' role can create a project."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('project-list-create')
        data = {'name': 'Admin Project', 'description': 'Should succeed'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_06_non_member_cannot_access_project_tasks(self):
        """Test that a user not in the project members list cannot access its tasks."""
        self.client.force_authenticate(user=self.non_member_user)
        url = reverse('project-task-list-create', kwargs={'project_id': self.project.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_07_member_can_access_project_tasks(self):
        """Test that a valid project member can access tasks."""
        self.client.force_authenticate(user=self.member_user)
        url = reverse('project-task-list-create', kwargs={'project_id': self.project.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_08_creator_can_update_project(self):
        """Test that the project creator can update the project details."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('project-detail-update', kwargs={'pk': self.project.id})
        data = {'name': 'Updated Project Name'}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, 'Updated Project Name')

    def test_09_non_creator_cannot_update_project(self):
        """Test that a standard member cannot update the project details."""
        self.client.force_authenticate(user=self.member_user)
        url = reverse('project-detail-update', kwargs={'pk': self.project.id})
        data = {'name': 'Hacked Project Name'}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- Celery Async Tests ---

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_10_bulk_import_tasks_creates_records(self):
        """Test that bulk_import_tasks successfully creates tasks synchronously when eager."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('bulk-import-tasks', kwargs={'project_id': self.project.id})
        
        tasks_payload = [
            {"title": "Eager Task 1", "priority": "high"},
            {"title": "Eager Task 2", "priority": "low"}
        ]
        
        # Ensure no tasks exist initially
        self.assertEqual(Task.objects.count(), 0)
        
        response = self.client.post(url, tasks_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        
        # Because CELERY_TASK_ALWAYS_EAGER=True is set, the task executes immediately
        self.assertEqual(Task.objects.count(), 2)
        self.assertTrue(Task.objects.filter(title="Eager Task 1").exists())
        
        
        
        