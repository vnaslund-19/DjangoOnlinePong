import json
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from game.models import PongGame
from game.logic import Game

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Handles new WebSocket connections."""
        self.game_key = self.scope['url_route']['kwargs']['game_key']
        self.room_group_name = f'game_{self.game_key}'

        # Assign a unique player ID (UUID)
        self.player_id = str(uuid.uuid4())

        # ✅ FIX: Properly Await Database Call
        self.game = await sync_to_async(self._sync_get_or_create_game)()
        print(f"DEBUG: self.game -> {self.game}, Status: {self.game.status}")

        # Assign the player to the game
        success = await self.assign_player(self.player_id)
        if not success:
            print(f"🚨 [connect] Game {self.game.game_key} is full or finished!")
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Auto-start when both players are present
        if self.game.player1_id and self.game.player2_id and self.game.status != "in_progress":
            await self.start_game()

    def _sync_get_or_create_game(self):
        """Sync method for fetching or creating a game."""
        game, created = PongGame.objects.get_or_create(
            game_key=uuid.UUID(self.game_key),
            defaults={"status": "pending"}
        )
        return game

    async def assign_player(self, player_id):
        """Ensures safe database modification when assigning players."""
        return await sync_to_async(self._sync_assign_player)(player_id)

    def _sync_assign_player(self, player_id):
        """Sync method to safely assign players without async issues."""
        if self.game.status == "finished":
            return False  

        if not self.game.player1_id:
            self.game.player1_id = player_id
        elif not self.game.player2_id:
            self.game.player2_id = player_id
        else:
            return False  

        self.game.save()
        return True

    async def disconnect(self, close_code):
        """Handles player disconnection."""
        await sync_to_async(self._sync_handle_disconnect)()

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    def _sync_handle_disconnect(self):
        """Sync method to handle player disconnection."""
        if self.player_id == self.game.player1_id:
            self.game.player1_id = None
        elif self.player_id == self.game.player2_id:
            self.game.player2_id = None

        self.game.save()

        if not self.game.player1_id and not self.game.player2_id:
            self.game.delete()

    async def receive(self, text_data):
        """Handles incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            action = data.get("action")

            if action == "move":
                direction = data.get("direction")
                await self.update_player_movement(direction)
            elif action == "ready":
                print("DEBUG: Player is ready.")  # ✅ Acknowledge the "ready" message
                return  
            else:
                await self.send(json.dumps({"status": "error", "message": f"Unknown action: {action}"}))

            # Update game state after movement
            await self.calculate_ball_position()
            await self.broadcast_game_state()

        except Exception as e:
            await self.send(json.dumps({"status": "error", "message": str(e)}))

    async def update_player_movement(self, direction):
        """Updates player movement based on direction."""
        await sync_to_async(self._sync_update_player_movement)(direction)

    def _sync_update_player_movement(self, direction):
        """Sync method to update player movement safely."""
        if self.player_id == self.game.player1_id:
            player_key = "player1"
        elif self.player_id == self.game.player2_id:
            player_key = "player2"
        else:
            return  # Ignore movement if player is not part of the game

        player_positions = self.game.player_positions
        current_y = player_positions[player_key]["y"]

        if direction == "UP":
            new_y = max(0, current_y - self.game.player_speed)
        elif direction == "DOWN":
            new_y = min(self.game.board_height - self.game.player_height, current_y + self.game.player_speed)
        else:
            new_y = current_y  # STOP

        player_positions[player_key]["y"] = new_y
        self.game.player_positions = player_positions
        self.game.save()

    async def start_game(self):
        """Starts the game when both players are ready."""
        await sync_to_async(self._sync_start_game)()

    def _sync_start_game(self):
        """Sync method to start game."""
        self.game.status = "in_progress"
        self.game.save()

    async def calculate_ball_position(self):
        """Updates ball movement based on game logic and saves it."""
        game_logic = Game(self.game)
        game_logic.update_ball_position()
        await sync_to_async(self._sync_save_game)()

    def _sync_save_game(self):
        """Sync method to save game state."""
        self.game.save()

    async def broadcast_game_state(self):
        """Broadcasts updated game state to all players."""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "game_update",
                "status": "game_update",
                "state": await sync_to_async(self.get_game_state)()
            }
        )

    @sync_to_async
    def get_game_state(self):
        """Returns the current game state."""
        return {
            "players": {
                "player1": {
                    "player_id": self.game.player1_id or "Waiting...",
                    **self.game.player_positions.get("player1", {"x": self.game.x_margin, "y": self.game.p_y_mid}),
                    "score": self.game.player1_score
                },
                "player2": {
                    "player_id": self.game.player2_id or "Waiting...",
                    **self.game.player_positions.get("player2", {"x": self.game.p2_xpos, "y": self.game.p_y_mid}),
                    "score": self.game.player2_score
                }
            },
            "ball": self.game.ball_position,
            "status": self.game.status
        }

    async def game_update(self, event):
        """Sends game updates to clients."""
        await self.send(text_data=json.dumps(event))

    async def game_start(self, event):
        """Sends game start notification to clients."""
        await self.send(text_data=json.dumps(event))

    async def player_disconnect(self, event):
        """Notifies clients when a player disconnects."""
        await self.send(text_data=json.dumps(event))
