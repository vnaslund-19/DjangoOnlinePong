from django.db import models
import uuid
import random
import math

class PongGame(models.Model):
    """Model representing an online 1v1 Pong game session."""
    
    # Players & Status
    player1_id = models.UUIDField(null=True, blank=True)  # Unique identifier for Player 1
    player2_id = models.UUIDField(null=True, blank=True)  # Unique identifier for Player 2

    connected_players = models.JSONField(default=list, blank=True)  # Ensures an empty list instead of NULL
    ready_players = models.JSONField(default=list, blank=True)
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),        # Waiting for second player
            ('in_progress', 'In Progress'),  # Game is actively being played
            ('finished', 'Finished')       # Game has ended
        ],
        default='pending'
    )
    
    game_key = models.UUIDField(default=uuid.uuid4, unique=True)  # Unique game session identifier
    
    # Game Configuration
    board_width = models.IntegerField(default=700)
    board_height = models.IntegerField(default=500)
    player_height = models.IntegerField(default=50)
    player_speed = models.IntegerField(default=5)
    ball_side = models.IntegerField(default=10)
    start_speed = models.FloatField(default=7.5)
    speed_up_multiple = models.FloatField(default=1.02)
    max_speed = models.IntegerField(default=20)
    points_to_win = models.IntegerField(default=3)

    # Default Positions
    player_positions = models.JSONField(default=dict)
    ball_position = models.JSONField(default=dict)

    # Scores
    player1_score = models.IntegerField(default=0)
    player2_score = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Computed properties for easier access
    @property
    def x_margin(self):
        return self.ball_side * 1.2

    @property
    def player_width(self):
        return self.ball_side * 1.2

    @property
    def p2_xpos(self):
        return self.board_width - self.x_margin - self.player_width

    @property
    def p_y_mid(self):
        return (self.board_height / 2) - (self.player_height / 2)

    @property
    def b_x_mid(self):
        return (self.board_width / 2) - (self.ball_side / 2)

    @property
    def b_y_mid(self):
        return (self.board_height / 2) - (self.ball_side / 2)

    def initialize_ball(self, direction=None):
        """Initializes the ball's starting position with a random velocity angle."""
        angle = random.uniform(-45, 45)
        direction = direction if direction is not None else random.choice([-1, 1])
        return {
            "x": self.b_x_mid,
            "y": self.b_y_mid,
            "xVel": self.start_speed * direction * math.cos(math.radians(angle)),
            "yVel": self.start_speed * math.sin(math.radians(angle))
        }

    def assign_player(self, player_id): # NEW, for mini project
        """Assigns a player to the game. If the second player joins, start the game."""
        if self.status == "finished":
            return False  # Game is over, don't accept new players

        if not self.player1_id:
            self.player1_id = player_id
        elif not self.player2_id:
            self.player2_id = player_id
            self.status = "in_progress"  # Start the game when the second player joins
        else:
            return False  # Game is already full

        self.save()
        return True

    def save(self, *args, **kwargs):
        """Ensures default game state is initialized without overwriting existing values."""
        if not self.player_positions:
            self.player_positions = {
                "player1": {"x": self.x_margin, "y": self.p_y_mid},
                "player2": {"x": self.p2_xpos, "y": self.p_y_mid}
            }
        if not self.ball_position:
            self.ball_position = self.initialize_ball()
        super().save(*args, **kwargs)

    def update_position(self, player, position):
        """Updates a player's paddle position."""
        if player not in ["player1", "player2"]:
            return
        updated_positions = self.player_positions.copy()
        updated_positions[player]["y"] = position["y"]
        updated_positions[player]["x"] = position.get("x", updated_positions[player]["x"])
        self.player_positions = updated_positions
        self.save()

    def update_ball_position(self, position):
        """Updates the ball's position and velocity."""
        updated_ball = self.ball_position.copy()
        updated_ball["x"] = position.get("x", updated_ball["x"])
        updated_ball["y"] = position.get("y", updated_ball["y"])
        updated_ball["xVel"] = position.get("xVel", updated_ball["xVel"])
        updated_ball["yVel"] = position.get("yVel", updated_ball["yVel"])
        self.ball_position = updated_ball
        self.save()

    def __str__(self):
        return f"Pong Game {self.id} (Key: {self.game_key}, Status: {self.status})"
