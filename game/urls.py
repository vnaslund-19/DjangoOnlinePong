from django.urls import path
from game.views import pong_game, join_match 

urlpatterns = [
    path("pong/", pong_game, name="pong_game"),
    path("match/join/", join_match, name="join_match"),  # New API endpoint
]
