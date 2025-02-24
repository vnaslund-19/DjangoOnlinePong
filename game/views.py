from django.shortcuts import render
from django.http import JsonResponse
from game.models import PongGame
import uuid

def pong_game(request):
    """Render the Pong game page."""
    return render(request, "game/index.html")

def join_match(request):
    """Assigns player to an available match or creates a new one."""
    # Find an available game
    open_game = PongGame.objects.filter(status="pending").first()
    
    if open_game:
        open_game.player2 = request.user
        open_game.status = "in_progress"
        open_game.save()
        return JsonResponse({"game_key": str(open_game.game_key)})

    # Create a new game
    new_game = PongGame.objects.create(player1=request.user, game_key=uuid.uuid4(), status="pending")
    return JsonResponse({"game_key": str(new_game.game_key)})


