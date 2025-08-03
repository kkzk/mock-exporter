from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST
import json

# Prometheusメトリクスのインスタンス
custom_gauge = Gauge('custom_metric_value', 'Custom metric value from web interface')

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
            
            # メトリクス値を更新
            custom_gauge.set(metric_value)
            
            return JsonResponse({'status': 'success', 'value': metric_value})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'POST method required'})
