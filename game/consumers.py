import json
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from game.models import PongGame  # Adjusted for minimal project
from game.logic import Game  # Game logic module

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Handles new WebSocket connections."""
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'game_{self.room_name}'

        # Fetch game instance
        self.game = await sync_to_async(self.get_game_by_key)(self.room_name)
        if not self.game:
            await self.close()
            return

        # Join WebSocket group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        """Handles disconnection of a player."""
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Handles incoming WebSocket messages from clients."""
        try:
            data = json.loads(text_data)
            action = data.get('action')
            direction = data.get('direction')

            if action == 'move' and direction:
                await self.update_player_movement(direction)
            elif action == 'ready':
                await self.mark_player_ready()

            await self.calculate_ball_position()
            await self.broadcast_game_state()

        except ValueError as e:
            await self.send(json.dumps({"status": "error", "message": str(e)}))
        except Exception:
            await self.send(json.dumps({"status": "error", "message": "Unexpected error"}))

    @sync_to_async
    def get_game_by_key(self, game_key):
        """Fetches a game instance using the game_key."""
        try:
            return PongGame.objects.get(game_key=uuid.UUID(game_key))
        except PongGame.DoesNotExist:
            return None

    @sync_to_async
    def update_player_movement(self, direction):
        """Updates player movement and persists changes."""
        player_positions = self.game.player_positions
        if "player1" not in player_positions or "player2" not in player_positions:
            return

        # Determine active player
        player_key = "player1" if len(self.game.ready_players) < 1 else "player2"
        current_y = player_positions[player_key]["y"]

        # Update position based on direction
        if direction == "UP":
            new_y = max(0, current_y - self.game.player_speed)
        elif direction == "DOWN":
            new_y = min(self.game.board_height - self.game.player_height, current_y + self.game.player_speed)
        else:
            new_y = current_y  # STOP

        player_positions[player_key]["y"] = new_y
        self.game.player_positions = player_positions
        self.game.save()

    async def mark_player_ready(self):
        """Marks a player as ready and starts the game when both are ready."""
        if len(self.game.ready_players) < 2:
            self.game.ready_players.append("player")
        
        if len(self.game.ready_players) == 2:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'game_start',
                    'status': 'game_starting',
                    'message': 'Both players are ready. Game is starting!'
                }
            )
            self.game.status = 'in_progress'
            await sync_to_async(self.game.save)()

    async def calculate_ball_position(self):
        """Updates ball movement based on game logic and saves the updated state."""
        game_logic = Game(self.game)
        game_logic.update_ball_position()
        await sync_to_async(self.game.save)()

    async def broadcast_game_state(self):
        """Broadcasts updated game state to all players."""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'game_update',
                'status': 'game_update',
                'state': await sync_to_async(self.get_game_state)()
            }
        )

    @sync_to_async
    def get_game_state(self):
        """Returns the current game state."""
        return {
            "players": {
                "player1": {
                    **self.game.player_positions.get("player1", {"x": self.game.x_margin, "y": self.game.p_y_mid}),
                    "score": self.game.player1_score
                },
                "player2": {
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
