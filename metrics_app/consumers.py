import json
from channels.generic.websocket import AsyncWebsocketConsumer

class WebhookConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # WebSocketクライアントをwebhook_messagesグループに追加
        await self.channel_layer.group_add(
            "webhook_messages",
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # WebSocketクライアントをwebhook_messagesグループから削除
        await self.channel_layer.group_discard(
            "webhook_messages",
            self.channel_name
        )

    async def receive(self, text_data):
        # クライアントからのメッセージを受信（今回は特に処理しない）
        pass

    # グループからのメッセージを受信してクライアントに送信
    async def webhook_message(self, event):
        message = event['message']
        
        # WebSocketクライアントにメッセージを送信
        await self.send(text_data=json.dumps({
            'type': 'webhook_message',
            'message': message
        }))
