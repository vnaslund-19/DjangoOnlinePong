from django.shortcuts import render
from django.http import JsonResponse
from game.models import PongGame
import uuid

def pong_game(request):
    """Render the Pong game page."""
    return render(request, "game/index.html")

def join_match(request):
    """Assigns player to an available match or creates a new one."""
    
    # ✅ Look for an existing game that is still pending and has only one player
    open_game = PongGame.objects.filter(status="pending", player2_id__isnull=True).first()

    if open_game:
        open_game.player2_id = str(uuid.uuid4())  # Assign a new unique player ID
        open_game.status = "in_progress"  # ✅ Start the game when the second player joins
        open_game.save()
        print(f"✅ [join_match] Assigned Player 2 to game: {open_game.game_key}")
        return JsonResponse({"game_key": str(open_game.game_key)})

    # ✅ If no open game exists, create a new one
    new_game = PongGame.objects.create(
        player1_id=str(uuid.uuid4()), 
        game_key=uuid.uuid4(), 
        status="pending"  # 🔥 ENSURE it's pending
    )
    print(f"✅ [join_match] Created new game: {new_game.game_key}, Status: {new_game.status}")
    
    return JsonResponse({"game_key": str(new_game.game_key)})
    