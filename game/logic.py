import math
import random
from game.models import PongGame  # Adjusted import

class Game:
    def __init__(self, game_instance: PongGame):
        """Initialize the game using an existing PongGame instance."""
        self.game = game_instance

        # Load stored game attributes
        self.board_width = game_instance.board_width
        self.board_height = game_instance.board_height
        self.player_height = game_instance.player_height
        self.player_width = game_instance.player_width
        self.player_speed = game_instance.player_speed
        self.ball_side = game_instance.ball_side
        self.start_speed = game_instance.start_speed
        self.speed_up_multiple = game_instance.speed_up_multiple
        self.max_speed = game_instance.max_speed
        self.points_to_win = game_instance.points_to_win
        self.x_margin = game_instance.x_margin
        self.p2_xpos = game_instance.p2_xpos
        self.p_y_mid = game_instance.p_y_mid
        self.b_x_mid = game_instance.b_x_mid
        self.b_y_mid = game_instance.b_y_mid

        # Ensure player positions exist
        self.game.player_positions.setdefault("player1", {"x": self.x_margin, "y": self.p_y_mid})
        self.game.player_positions.setdefault("player2", {"x": self.p2_xpos, "y": self.p_y_mid}) 

        # Initialize ball position
        if self.game.ball_position:
            self.ball = self.game.ball_position
            if "speed" not in self.ball:  # Ensure speed is set
                self.ball["speed"] = self.start_speed
        else:
            self._reset_ball(0)  # No one scored, game start

    def _reset_ball(self, scored):
        """Reset the ball to the center of the board with a random initial velocity."""
        angle = math.radians(random.uniform(-45, 45))
        direction = 1 if scored == 1 else -1 if scored == 2 else random.choice([-1, 1])

        # Store the ball state and persist to database
        self.ball = {
            "x": self.b_x_mid,
            "y": self.b_y_mid,
            "xVel": self.start_speed * math.cos(angle) * direction,
            "yVel": self.start_speed * math.sin(angle),
            "speed": self.start_speed
        }
        self.game.update_ball_position(self.ball)

    def update_player_movement(self, player, direction):
        """Updates player movement & persists it in the database."""
        if self.game.status == "finished":
            return

        current_y = self.game.player_positions[player]["y"]

        # Update position based on direction
        if direction == "UP":
            new_y = max(0, current_y - self.player_speed)
        elif direction == "DOWN":
            new_y = min(self.board_height - self.player_height, current_y + self.player_speed)
        else:
            new_y = current_y  # STOP

        # Preserve X-position
        current_x = self.game.player_positions[player].get("x", self.x_margin if player == "player1" else self.p2_xpos)

        # Save new position
        self.game.update_position(player, {"x": current_x, "y": new_y})
        self.game.save()

    def update_ball_position(self):
        """Updates the ball's position, handles collisions, and persists it."""
        if self.game.status == "finished":
            return

        ball = self.ball
        ball["x"] += ball["xVel"]
        ball["y"] += ball["yVel"]

        # Ball collision with top/bottom walls
        if ball["y"] <= 0 or ball["y"] + self.ball_side >= self.board_height:
            ball["yVel"] *= -1  # Reverse Y direction

        # Ball collision with paddles
        self._handle_paddle_hit("player1")
        self._handle_paddle_hit("player2")

        # Check if a player scored
        if ball["x"] <= 0:  # Player 2 scores
            self.game.player2_score += 1
            self._check_game_over()
            self._reset_ball(2)
        elif ball["x"] + self.ball_side >= self.board_width:  # Player 1 scores
            self.game.player1_score += 1
            self._check_game_over()
            self._reset_ball(1)

        self.game.update_ball_position(self.ball)
        self.game.save()

    def _handle_paddle_hit(self, player):
        """Handles ball collision with paddles, calculating rebound angles."""
        paddle = self.game.player_positions.get(player)
        if not paddle:
            return

        paddle_x, paddle_y = paddle["x"], paddle["y"]
        ball = self.ball  

        # Check if the ball is colliding with the paddle
        if ((ball["x"] < paddle_x + self.player_width) and   
            (ball["x"] + self.ball_side > paddle_x) and      
            (ball["y"] < paddle_y + self.player_height) and  
            (ball["y"] + self.ball_side > paddle_y)):

            # Calculate relative collision position
            collision_point = ball["y"] - paddle_y - self.player_height / 2 + self.ball_side / 2
            collision_point = max(-self.player_height / 2, min(self.player_height / 2, collision_point))
            collision_point /= (self.player_height / 2)

            # Compute rebound angle (max ±45 degrees)
            rebound_angle = (math.pi / 4) * collision_point

            # Increase speed slightly with each hit
            if ball["speed"] < self.max_speed:
                ball["speed"] *= self.speed_up_multiple

            # Calculate new velocity components
            ball["xVel"] = ball["speed"] * math.cos(rebound_angle)
            ball["yVel"] = ball["speed"] * math.sin(rebound_angle)

            # Ensure the ball moves in the correct direction after bouncing
            ball["xVel"] = abs(ball["xVel"]) if player == "player1" else -abs(ball["xVel"])

    def _check_game_over(self):
        """Check if a player has won the game and persist scores."""
        if self.game.player1_score >= self.points_to_win:
            self.game.winner = self.game.player1
        elif self.game.player2_score >= self.points_to_win:
            self.game.winner = self.game.player2

        if self.game.winner:
            self.game.status = "finished"
            self.game.save()

    def get_game_state(self):
        """Return the current game state as a dictionary."""
        return {
            "ball": self.ball,
            "players": {
                "player1": self.game.player_positions.get("player1", {"x": self.x_margin, "y": self.p_y_mid}), 
                "player2": self.game.player_positions.get("player2", {"x": self.p2_xpos, "y": self.p_y_mid})
            },
            "status": self.game.status,
            "winner": self.game.winner.username if self.game.winner else None
        }
