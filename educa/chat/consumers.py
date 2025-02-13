import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone
from chat.models import Message


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Accepts the WebSocket connection."""
        self.user = self.scope['user']
        self.id = self.scope['url_route']['kwargs']['course_id']
        self.room_group_name = f'chat_{self.id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        # Accept connection
        await self.accept()

    async def disconnect(self, close_code):
        """Handles WebSocket disconnection."""
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def persist_message(self, message):
        """Saves the message to the database."""
        await Message.objects.acreate(
            user=self.user,
            course_id=self.id,
            content=message
        )

    async def receive(self, text_data):
        """Receives messages from WebSocket and sends them to the group."""
        text_data_json = json.loads(text_data)
        message = text_data_json.get('message')
        now = timezone.now()

        if message:
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'user': self.user.username,
                    'datetime': now.isoformat(),
                }
            )

            # Persist message
            await self.persist_message(message)

    async def chat_message(self, event):
        """Handles messages sent to the group and forwards them to the WebSocket."""
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'user': event['user'],
            'datetime': event['datetime'],
        }))
