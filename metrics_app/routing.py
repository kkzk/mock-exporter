from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/webhook/$', consumers.WebhookConsumer.as_asgi()),
    re_path(r'ws/webhook_messages/$', consumers.WebhookConsumer.as_asgi()),
]
