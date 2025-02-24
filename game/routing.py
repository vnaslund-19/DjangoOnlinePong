from django.urls import re_path
from game.consumers import GameConsumer

websocket_urlpatterns = [
    re_path(r'ws/game/(?P<game_key>[0-9a-f-]{36})/$', GameConsumer.as_asgi()),  # ✅ FIXED REGEX FOR UUID
]
