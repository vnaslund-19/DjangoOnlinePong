import json
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from game.models import PongGame
from game.logic import Game

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Handles new WebSocket connections."""
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'game_{self.room_name}'

        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close()
            return

        # Fetch or create game
        self.game = await sync_to_async(self.get_or_create_game)(self.room_name, self.user)
        
        if self.user not in [self.game.player1, self.game.player2]:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Auto-start when both players are present
        if self.game.player1 and self.game.player2 and self.game.status != "in_progress":
            await self.start_game()

    @sync_to_async
    def get_or_create_game(self, game_key, user):
        """Fetches an existing game or creates a new one."""
        game, created = PongGame.objects.get_or_create(
            game_key=uuid.UUID(game_key),
            defaults={"status": "pending", "player1": user}
        )
        if not created and game.status == "pending" and game.player1 != user and not game.player2:
            game.player2 = user
            game.save()
        return game

    async def disconnect(self, close_code):
        """Handles player disconnection."""
        if self.user == self.game.player1:
            self.game.player1 = None
        elif self.user == self.game.player2:
            self.game.player2 = None

        await sync_to_async(self.game.save)()

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        # Notify other player if someone disconnects
        if not self.game.player1 and not self.game.player2:
            await sync_to_async(self.game.delete)()
        else:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'player_disconnect',
                    'status': 'player_disconnected',
                    'message': f'{self.user.username} has disconnected.'
                }
            )

    async def receive(self, text_data):
        """Handles incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            action = data.get("action")
            direction = data.get("direction")

            if action == "move":
                await self.update_player_movement(direction)
            else:
                await self.send(json.dumps({"status": "error", "message": f"Unknown action: {action}"}))

            # Update game state after movement
            await self.calculate_ball_position()
            await self.broadcast_game_state()

        except Exception as e:
            await self.send(json.dumps({"status": "error", "message": str(e)}))

    @sync_to_async
    def update_player_movement(self, direction):
        """Updates player movement based on direction."""
        player_key = "player1" if self.user == self.game.player1 else "player2"

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
        self.game.status = "in_progress"
        await sync_to_async(self.game.save)()

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "game_start",
                "status": "game_starting",
                "message": "Game is starting now!"
            }
        )

    async def calculate_ball_position(self):
        """Updates ball movement based on game logic and saves it."""
        game_logic = Game(self.game)
        game_logic.update_ball_position()
        await sync_to_async(self.game.save)()

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
                    "username": self.game.player1.username if self.game.player1 else "Waiting...",
                    **self.game.player_positions.get("player1", {"x": self.game.x_margin, "y": self.game.p_y_mid}),
                    "score": self.game.player1_score
                },
                "player2": {
                    "username": self.game.player2.username if self.game.player2 else "Waiting...",
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
