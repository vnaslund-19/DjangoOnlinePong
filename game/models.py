from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
import uuid
import random
import math

class User(AbstractUser):
    """Custom user model with necessary Pong game tracking."""
    username = models.CharField(max_length=150, unique=True)
    friends = models.ManyToManyField('self', symmetrical=True, blank=True)

    # Fix auth conflicts
    groups = models.ManyToManyField(Group, related_name="game_users", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="game_users_permissions", blank=True)

    @property
    def games(self):
        """Returns all games where this user is either player1 or player2."""
        return self.player1_games.all() | self.player2_games.all()

    def __str__(self):
        return self.username


class PongGame(models.Model):
    """Model representing a basic Pong game session."""
    
    # Players & Status
    player1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='player1_games')
    player2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='player2_games')
    winner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_games')
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('in_progress', 'In Progress'),
            ('finished', 'Finished')
        ],
        default='pending'
    )
    
    game_key = models.UUIDField(default=uuid.uuid4, unique=True)  # Unique game session identifier
    connected_players = models.JSONField(default=list)  # Tracks active WebSocket connections
    ready_players = models.JSONField(default=list)  # Tracks players ready to start
    
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

    def get_opponent(self, user):
        """Returns the opponent user in the game."""
        return self.player2 if self.player1 == user else self.player1

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
        return f"Game {self.id}: {self.player1} vs {self.player2} (Key: {self.game_key})"
