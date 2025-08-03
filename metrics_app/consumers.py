import json
from channels.generic.websocket import AsyncWebsocketConsumer

class WebhookConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # WebSocketクライアントをwebhook_messagesグループに追加
        await self.channel_layer.group_add(
            "webhook_messages",
            self.channel_name
        )
        # WebSocketクライアントをmetrics_syncグループに追加（スライダー同期用）
        await self.channel_layer.group_add(
            "metrics_sync",
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # WebSocketクライアントをwebhook_messagesグループから削除
        await self.channel_layer.group_discard(
            "webhook_messages",
            self.channel_name
        )
        # WebSocketクライアントをmetrics_syncグループから削除
        await self.channel_layer.group_discard(
            "metrics_sync",
            self.channel_name
        )

    async def receive(self, text_data):
        # クライアントからのメッセージを受信
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'metric_update':
                # スライダー値の更新をグループの他のクライアントに送信
                metric_id = text_data_json.get('metric_id')
                metric_name = text_data_json.get('metric_name')
                prometheus_name = text_data_json.get('prometheus_name')
                metric_value = text_data_json.get('metric_value')
                
                await self.channel_layer.group_send(
                    "metrics_sync",
                    {
                        "type": "metric_sync",
                        "metric_id": metric_id,
                        "metric_name": metric_name,
                        "prometheus_name": prometheus_name,
                        "metric_value": metric_value,
                        "sender_channel": self.channel_name
                    }
                )
        except json.JSONDecodeError:
            # 無効なJSONの場合は無視
            pass

    # グループからのwebhookメッセージを受信してクライアントに送信
    async def webhook_message(self, event):
        message = event['message']
        
        # WebSocketクライアントにメッセージを送信
        await self.send(text_data=json.dumps({
            'type': 'webhook_message',
            'message': message
        }))

    # グループからのメトリクス同期メッセージを受信してクライアントに送信
    async def metric_sync(self, event):
        # 送信者と同じクライアントには送信しない
        if event.get('sender_channel') != self.channel_name:
            await self.send(text_data=json.dumps({
                'type': 'metric_sync',
                'metric_id': event.get('metric_id'),
                'metric_name': event['metric_name'],
                'prometheus_name': event.get('prometheus_name'),
                'metric_value': event['metric_value']
            }))

    # メトリクス一覧の更新通知を受信してクライアントに送信
    async def metrics_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'metrics_update'
        }))
