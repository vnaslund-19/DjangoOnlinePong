from django.urls import re_path
from game.consumers import GameConsumer

websocket_urlpatterns = [
    re_path(r'ws/game/(?P<game_key>\w+)/$', GameConsumer.as_asgi()),
]
