from django.urls import re_path
from game.consumers import GameConsumer

websocket_urlpatterns = [
    re_path(r'ws/game/(?P<game_key>[0-9a-fA-F-]{36})/$', GameConsumer.as_asgi()),  # Supports uppercase hex values
]
