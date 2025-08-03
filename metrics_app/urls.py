from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('metrics', views.metrics, name='metrics'),
    path('update_metric/', views.update_metric, name='update_metric'),
    path('webhook/', views.webhook, name='webhook'),
    path('get_webhook_messages/', views.get_webhook_messages, name='get_webhook_messages'),
    path('get_current_metrics/', views.get_current_metrics, name='get_current_metrics'),
]
