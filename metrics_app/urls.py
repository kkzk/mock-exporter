from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('metrics', views.metrics, name='metrics'),
    path('update_metric/', views.update_metric, name='update_metric'),
    path('webhook/', views.webhook, name='webhook'),
    path('get_webhook_messages/', views.get_webhook_messages, name='get_webhook_messages'),
    path('get_current_metrics/', views.get_current_metrics, name='get_current_metrics'),
    path('get_metrics_list/', views.get_metrics_list, name='get_metrics_list'),
    path('create_metric/', views.create_metric, name='create_metric'),
    path('select_metric/', views.select_metric, name='select_metric'),
    path('delete_metric/', views.delete_metric, name='delete_metric'),
    path('cleanup_metrics/', views.cleanup_metrics, name='cleanup_metrics'),
]
