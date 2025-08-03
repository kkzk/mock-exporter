from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST
import json
from datetime import datetime
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

# Prometheusメトリクスのインスタンス
custom_gauge = Gauge('custom_metric_value', 'Custom metric value from web interface')

# webhookメッセージを保存するリスト（実際のプロダクションではデータベースを使用）
webhook_messages = []

# 現在のメトリクス値を保存（複数ブラウザ間での同期用）
current_metrics = {
    'metric_name': 'custom_application_metric',
    'metric_value': 50
}

def index(request):
    """メイン画面を表示"""
    return render(request, 'metrics_app/index.html')

def metrics(request):
    """Prometheusメトリクスエンドポイント"""
    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)

@csrf_exempt
def update_metric(request):
    """メトリクス値を更新"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            metric_name = data.get('metric_name', 'default_metric')
            metric_value = float(data.get('metric_value', 0))
            
            # グローバルな現在値を更新
            current_metrics['metric_name'] = metric_name
            current_metrics['metric_value'] = metric_value
            
            # メトリクス値を更新
            custom_gauge.set(metric_value)
            
            # WebSocketで他のクライアントに通知
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "metrics_sync",
                {
                    "type": "metric_sync",
                    "metric_name": metric_name,
                    "metric_value": metric_value,
                    "sender_channel": None  # サーバーからの更新
                }
            )
            
            return JsonResponse({'status': 'success', 'value': metric_value})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'POST method required'})

@csrf_exempt
def webhook(request):
    """webhookエンドポイント - 外部からのメッセージを受信"""
    if request.method == 'POST':
        try:
            # リクエストボディからデータを取得
            content_type = request.content_type
            
            if 'application/json' in content_type:
                data = json.loads(request.body)
                message = data.get('message', 'No message provided')
            else:
                # プレーンテキストの場合
                message = request.body.decode('utf-8')
            
            # メッセージを保存（タイムスタンプ付き）
            webhook_message = {
                'message': message,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'content_type': content_type
            }
            webhook_messages.append(webhook_message)
            
            # 最新の100件のみ保持
            if len(webhook_messages) > 100:
                webhook_messages.pop(0)
            
            # WebSocketでリアルタイム通知を送信
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "webhook_messages",
                {
                    "type": "webhook_message",
                    "message": webhook_message
                }
            )
            
            return JsonResponse({
                'status': 'success', 
                'message': 'Webhook received successfully',
                'received_message': message
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'POST method required'})

def get_webhook_messages(request):
    """webhookメッセージを取得するAPI"""
    return JsonResponse({
        'status': 'success',
        'messages': webhook_messages[-20:]  # 最新20件を返す
    })

def get_current_metrics(request):
    """現在のメトリクス値を取得するAPI"""
    return JsonResponse({
        'status': 'success',
        'metric_name': current_metrics['metric_name'],
        'metric_value': current_metrics['metric_value']
    })
