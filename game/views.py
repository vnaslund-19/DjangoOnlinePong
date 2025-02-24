from django.shortcuts import render
from django.http import JsonResponse
from game.models import PongGame
import uuid

def pong_game(request):
    """Render the Pong game page."""
    return render(request, "game/index.html")

def join_match(request):
    """Assigns player to an available match or creates a new one."""
    player_id = str(uuid.uuid4())  # Assign a unique player ID

    # Check for an open game
    open_game = PongGame.objects.filter(status="pending", player1_id__isnull=False, player2_id__isnull=True).first()

    if open_game:
        open_game.player2_id = player_id  # Assign the second player
        open_game.status = "in_progress"
        open_game.save()
        return JsonResponse({"game_key": str(open_game.game_key), "player_id": player_id})

    # No open game found, create a new game
    new_game = PongGame.objects.create(player1_id=player_id, game_key=uuid.uuid4(), status="pending")
    return JsonResponse({"game_key": str(new_game.game_key), "player_id": player_id})
