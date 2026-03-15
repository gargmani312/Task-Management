import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from user.models import Project

class ProjectConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.project_id = self.scope['url_route']['kwargs']['project_id']
        self.room_group_name = f'project_{self.project_id}'
        user = self.scope['user']

        if not user.is_authenticated:
            await self.close()
            return

        is_member = await self.check_project_member(user, self.project_id)
        if not is_member:
            await self.close()
            return


        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    @database_sync_to_async
    def check_project_member(self, user, project_id):
        try:
            project = Project.objects.get(id=project_id)
            return project.members.filter(id=user.id).exists()
        except Project.DoesNotExist:
            return False

    async def send_event(self, event):
        await self.send(text_data=json.dumps(event['data']))

    async def task_created(self, event):
        await self.send_event(event)

    async def task_updated(self, event):
        await self.send_event(event)

    async def new_comment(self, event):
        await self.send_event(event)
        
        
        