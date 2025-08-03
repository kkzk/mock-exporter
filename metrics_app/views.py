from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST, REGISTRY
import json
from datetime import datetime
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import re

# 動的に作成されたメトリクスを保存する辞書（ID管理）
metrics_registry = {}

# webhookメッセージを保存するリスト（実際のプロダクションではデータベースを使用）
webhook_messages = []

# 現在のメトリクス値を保存（ID管理）
current_metrics = {}

# メトリクスIDカウンター
metric_id_counter = 0

# 現在選択中のメトリクスID
current_metric_id = None

def initialize_default_metrics():
    """初期メトリクスを作成"""
    if not metrics_registry:  # まだメトリクスが作成されていない場合のみ
        create_new_metric("custom_metric_value")

def get_next_metric_id():
    """次のメトリクスIDを取得"""
    global metric_id_counter
    metric_id_counter += 1
    return metric_id_counter

def create_new_metric(metric_name="new_metric"):
    """新しいメトリクスを作成"""
    global current_metric_id
    
    metric_id = get_next_metric_id()
    prometheus_name = convert_to_prometheus_name(metric_name)
    
    try:
        # 新しいメトリクスを作成
        gauge = Gauge(prometheus_name, f"Dynamic metric {metric_id} created from web interface")
        
        metrics_registry[metric_id] = {
            'gauge': gauge,
            'original_name': metric_name,
            'prometheus_name': prometheus_name,
            'created_at': datetime.now().isoformat()
        }
        
        current_metrics[metric_id] = {
            'original_name': metric_name,
            'prometheus_name': prometheus_name,
            'value': 0
        }
        
        # 新しく作成したメトリクスを現在選択中に設定
        current_metric_id = metric_id
        
        print(f"Created new metric: ID={metric_id}, name={prometheus_name}")
        return metric_id
        
    except Exception as e:
        print(f"Error creating metric: {e}")
        return None

def convert_to_prometheus_name(metric_name):
    """メトリクス名をPrometheus形式に変換"""
    prometheus_name = re.sub(r'[^a-zA-Z0-9_]', '_', metric_name)
    prometheus_name = re.sub(r'_+', '_', prometheus_name)
    prometheus_name = prometheus_name.strip('_')
    
    if not prometheus_name:
        prometheus_name = 'unnamed_metric'
    
    return prometheus_name

def update_metric_name(metric_id, new_name):
    """既存メトリクスの名前を更新"""
    if metric_id not in metrics_registry:
        return False
    
    old_prometheus_name = metrics_registry[metric_id]['prometheus_name']
    new_prometheus_name = convert_to_prometheus_name(new_name)
    
    # 同名のメトリクスが他に存在するかチェック
    for existing_id, info in metrics_registry.items():
        if existing_id != metric_id and info['prometheus_name'] == new_prometheus_name:
            new_prometheus_name = f"{new_prometheus_name}_{metric_id}"
            break
    
    try:
        # 新しい名前でメトリクスを再作成
        old_gauge = metrics_registry[metric_id]['gauge']
        old_value = current_metrics[metric_id]['value']
        
        # 古いメトリクスを削除
        REGISTRY.unregister(old_gauge)
        
        # 新しいメトリクスを作成
        new_gauge = Gauge(new_prometheus_name, f"Dynamic metric {metric_id} created from web interface")
        new_gauge.set(old_value)
        
        # 情報を更新
        metrics_registry[metric_id]['gauge'] = new_gauge
        metrics_registry[metric_id]['original_name'] = new_name
        metrics_registry[metric_id]['prometheus_name'] = new_prometheus_name
        
        current_metrics[metric_id]['original_name'] = new_name
        current_metrics[metric_id]['prometheus_name'] = new_prometheus_name
        
        print(f"Updated metric name: ID={metric_id}, {old_prometheus_name} -> {new_prometheus_name}")
        return True
        
    except Exception as e:
        print(f"Error updating metric name: {e}")
        return False

def delete_metric_by_id(metric_id):
    """IDでメトリクスを削除"""
    if metric_id not in metrics_registry:
        return False
    
    try:
        # Prometheusレジストリから削除
        gauge = metrics_registry[metric_id]['gauge']
        REGISTRY.unregister(gauge)
        
        # 内部レジストリから削除
        del metrics_registry[metric_id]
        del current_metrics[metric_id]
        
        # 現在選択中のメトリクスだった場合は、他のメトリクスを選択
        global current_metric_id
        if current_metric_id == metric_id:
            if metrics_registry:
                current_metric_id = next(iter(metrics_registry.keys()))
            else:
                current_metric_id = None
        
        print(f"Deleted metric: ID={metric_id}")
        return True
        
    except Exception as e:
        print(f"Error deleting metric: {e}")
        return False

def index(request):
    """メイン画面を表示"""
    # 初期メトリクスを作成
    initialize_default_metrics()
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
            metric_id = data.get('metric_id')
            metric_name = data.get('metric_name')
            metric_value = data.get('metric_value')
            
            # メトリクスIDが指定されていない場合は現在選択中のメトリクスを使用
            if metric_id is None:
                metric_id = current_metric_id
            
            if metric_id is None:
                return JsonResponse({'status': 'error', 'message': 'No metric selected'})
            
            # メトリクス名が変更された場合は名前を更新
            if metric_name is not None and metric_id in metrics_registry:
                if metrics_registry[metric_id]['original_name'] != metric_name:
                    update_metric_name(metric_id, metric_name)
            
            # メトリクス値が指定された場合は値を更新
            if metric_value is not None:
                if metric_id in metrics_registry:
                    metric_value = float(metric_value)
                    metrics_registry[metric_id]['gauge'].set(metric_value)
                    current_metrics[metric_id]['value'] = metric_value
            
            # 現在のメトリクス情報を取得
            if metric_id in metrics_registry:
                metric_info = metrics_registry[metric_id]
                current_info = current_metrics[metric_id]
                
                # WebSocketで他のクライアントに通知
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    "metrics_sync",
                    {
                        "type": "metric_sync",
                        "metric_id": metric_id,
                        "metric_name": current_info['original_name'],
                        "prometheus_name": current_info['prometheus_name'],
                        "metric_value": current_info['value'],
                        "sender_channel": None  # サーバーからの更新
                    }
                )
                
                return JsonResponse({
                    'status': 'success',
                    'metric_id': metric_id,
                    'original_name': current_info['original_name'],
                    'prometheus_name': current_info['prometheus_name'],
                    'value': current_info['value']
                })
            else:
                return JsonResponse({'status': 'error', 'message': 'Metric not found'})
                
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
                    "message": f"[{webhook_message['timestamp']}] {webhook_message['message']}"
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
    # 初期メトリクスを作成
    initialize_default_metrics()
    
    metrics_data = []
    for metric_id, info in current_metrics.items():
        metrics_data.append({
            'metric_id': metric_id,
            'original_name': info['original_name'],
            'prometheus_name': info['prometheus_name'],
            'value': info['value']
        })
    
    return JsonResponse({
        'status': 'success',
        'metrics': metrics_data,
        'current_metric_id': current_metric_id
    })

def get_metrics_list(request):
    """利用可能なメトリクス一覧を取得するAPI"""
    # 初期メトリクスを作成
    initialize_default_metrics()
    
    metrics_list = []
    for metric_id, info in current_metrics.items():
        metrics_list.append({
            'metric_id': metric_id,
            'original_name': info['original_name'],
            'prometheus_name': info['prometheus_name'],
            'value': info['value']
        })
    
    return JsonResponse({
        'status': 'success',
        'metrics': metrics_list,
        'current_metric_id': current_metric_id
    })

def generate_unique_metric_name(base_name="new_metric"):
    """重複しないメトリクス名を生成"""
    prometheus_base = convert_to_prometheus_name(base_name)
    
    # 既存のメトリクス名を確認
    existing_names = set()
    for info in metrics_registry.values():
        existing_names.add(info['prometheus_name'])
    
    # ベース名が使用可能かチェック
    if prometheus_base not in existing_names:
        return base_name
    
    # 連番を付けて重複しない名前を生成
    counter = 1
    while True:
        candidate_name = f"{base_name}_{counter}"
        candidate_prometheus = convert_to_prometheus_name(candidate_name)
        if candidate_prometheus not in existing_names:
            return candidate_name
        counter += 1

@csrf_exempt
def create_metric(request):
    """新しいメトリクスを作成する"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            metric_name = data.get('metric_name')
            
            # メトリクス名が指定されていない場合は自動生成
            if not metric_name:
                metric_name = generate_unique_metric_name("new_metric")
            
            metric_id = create_new_metric(metric_name)
            if metric_id:
                # WebSocketで他のクライアントに通知
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    "webhook_messages",
                    {
                        "type": "webhook_message",
                        "message": f"新しいメトリクス '{metric_name}' が作成されました"
                    }
                )
                
                # メトリクス一覧の更新を通知
                async_to_sync(channel_layer.group_send)(
                    "metrics_sync",
                    {
                        "type": "metrics_update"
                    }
                )
                
                return JsonResponse({
                    'status': 'success',
                    'metric_id': metric_id,
                    'message': f'Metric created successfully',
                    'metric': current_metrics[metric_id]
                })
            else:
                return JsonResponse({'status': 'error', 'message': 'Failed to create metric'})
                
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'POST method required'})

@csrf_exempt
def select_metric(request):
    """現在選択中のメトリクスを変更する"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            metric_id = data.get('metric_id')
            
            if metric_id is None:
                return JsonResponse({'status': 'error', 'message': 'metric_id is required'})
            
            metric_id = int(metric_id)
            if metric_id not in metrics_registry:
                return JsonResponse({'status': 'error', 'message': 'Metric not found'})
            
            global current_metric_id
            current_metric_id = metric_id
            
            return JsonResponse({
                'status': 'success',
                'current_metric_id': current_metric_id,
                'metric': current_metrics[metric_id]
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'POST method required'})

@csrf_exempt
def delete_metric(request):
    """指定されたメトリクスを削除する"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            metric_id = data.get('metric_id')
            
            if metric_id is None:
                return JsonResponse({'status': 'error', 'message': 'metric_id is required'})
            
            metric_id = int(metric_id)
            
            # 削除前にメトリクス名を取得
            metric_name = current_metrics.get(metric_id, {}).get('original_name', 'Unknown')
            
            if delete_metric_by_id(metric_id):
                # WebSocketで他のクライアントに通知
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    "webhook_messages",
                    {
                        "type": "webhook_message",
                        "message": f"メトリクス '{metric_name}' が削除されました"
                    }
                )
                
                # メトリクス一覧の更新を通知
                async_to_sync(channel_layer.group_send)(
                    "metrics_sync",
                    {
                        "type": "metrics_update"
                    }
                )
                
                return JsonResponse({
                    'status': 'success',
                    'message': f'Metric deleted successfully',
                    'current_metric_id': current_metric_id
                })
            else:
                return JsonResponse({'status': 'error', 'message': 'Failed to delete metric'})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'POST method required'})

@csrf_exempt
def cleanup_metrics(request):
    """全てのメトリクスをクリーンアップする"""
    try:
        global current_metric_id
        
        metrics_count = len(metrics_registry)
        
        # 全てのメトリクスを削除
        for metric_id in list(metrics_registry.keys()):
            delete_metric_by_id(metric_id)
        
        current_metric_id = None
        
        # WebSocketで他のクライアントに通知
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "webhook_messages",
            {
                "type": "webhook_message",
                "message": f"全メトリクス ({metrics_count}個) が削除されました"
            }
        )
        
        # メトリクス一覧の更新を通知
        async_to_sync(channel_layer.group_send)(
            "metrics_sync",
            {
                "type": "metrics_update"
            }
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'All metrics cleared',
            'remaining_metrics': len(metrics_registry)
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
