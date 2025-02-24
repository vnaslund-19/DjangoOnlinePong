// Board
let board;
let context;

// Variables provided by user (initialized in global scope)
let startSpeed;
let speedUpMultiple;
let playerHeight = 50;
let playerSpeed;
let allowPowerUp;
let boardWidth = 700; // Added values to now as they´re used in first version of onlinepong
let boardHeight = 500;
let pointsToWin;
let ballSide = 10;

// Depend on user provided variables
let xMargin; // Margin from paddle to side of board
let playerWidth = 12; // HARDCODED FOR ONLINE PONG
let yMax;
 
const   serveSpeedMultiple = 0.3;

// To set in the global scope
let ball = {};
let Lplayer = {};
let Rplayer = {};
let keyState = {};

let AImargin;
let predictedY;

const accentColor = getComputedStyle(document.documentElement).getPropertyValue('--lorange').trim();
const lightColor = getComputedStyle(document.documentElement).getPropertyValue('--light').trim();
const dangerColor = getComputedStyle(document.documentElement).getPropertyValue('--danger').trim();

let playerId = null;  // Store player ID globally

document.addEventListener("DOMContentLoaded", async () => {
    await connectToOnlineGame();  // Connect immediately when the page loads
});

async function connectToOnlineGame() {
    try {
        // Fetch or create a new game session
        const response = await fetch("http://localhost:8000/match/join/");
        if (!response.ok) throw new Error("Failed to join online match");

        const data = await response.json();
        if (data && data.game_key && data.player_id) {
            console.log("Connected to game session:", data.game_key);
            playerId = data.player_id;  // Store player ID globally
            return setupWebSocket(data.game_key);
        }
    } catch (error) {
        console.error("Error joining online match:", error);
    }
}


function setupWebSocket(gameKey)
{
    const socket = new WebSocket(`ws://localhost:8000/ws/game/${gameKey}/`);

    // Init game board
    const board = document.getElementById("board");
    board.width = 700;
    board.height = 500;
    const context = board.getContext("2d");

    socket.onopen = () => {
        console.log("WebSocket connected:", gameKey);
        if (playerId) {
            socket.send(JSON.stringify({ action: "ready", player_id: playerId })); // Send player ID
        }
    };

    socket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        console.log("Received WebSocket message:", message);

        if (message.status === "game_starting") {
            console.log("Game is starting!");
            document.addEventListener("keydown", (event) => keyDownHandlerOnline(event, socket));
            document.addEventListener("keyup", (event) => keyUpHandlerOnline(event, socket));
        } else if (message.status === "game_update") {
            updateGameState(message.state);
        }
    };

    window.addEventListener("beforeunload", () => {
        if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ action: "move", player_id: playerId, direction: "STOP" }));
        }
    });

    socket.onclose = () => {
        console.log("WebSocket Closed.");
        document.removeEventListener("keydown", keyDownHandlerOnline);
        document.removeEventListener("keyup", keyUpHandlerOnline);
    };

    socket.onerror = (error) => console.error("WebSocket Error:", error);
}


function updateGameState(state) {
    if (!state || !state.players || !state.ball) return; // Ensure valid data

    // Update paddle positions and scores
    if (state.players.player1) {
        Lplayer.x = state.players.player1.x;
        Lplayer.y = state.players.player1.y;
        Lplayer.score = state.players.player1.score;
    }
    
    if (state.players.player2) {
        Rplayer.x = state.players.player2.x;
        Rplayer.y = state.players.player2.y;
        Rplayer.score = state.players.player2.score;
    }

    // Update ball position
    ball.x = state.ball.x;
    ball.y = state.ball.y;

    renderGame();
}

function renderGame() {
    const context = document.getElementById("board").getContext("2d");

    context.clearRect(0, 0, 700, 500); // Clear the board

    // Draw center dashed line
    context.fillStyle = "white";
    for (let i = 10; i < 500; i += 25) {
        context.fillRect(345, i, 5, 5);
    }

    // Draw ball
    context.fillRect(ball.x, ball.y, 10, 10);

    // Draw scores
    context.font = "45px Arial";
    context.fillText(Lplayer.score, 140, 45);
    context.fillText(Rplayer.score, 490, 45);

    // Draw paddles
    context.fillRect(Lplayer.x, Lplayer.y, 10, 50);
    context.fillRect(Rplayer.x, Rplayer.y, 10, 50);
}

function keyDownHandlerOnline(event, socket) {
    if (["KeyW", "KeyS", "ArrowUp", "ArrowDown"].includes(event.code)) event.preventDefault();
    if (socket.readyState !== WebSocket.OPEN || !playerId) return;  // Ensure playerId exists

    let direction = null;

    if (event.code === "KeyW") {
        keyState.w = true;
        direction = "UP";
    } else if (event.code === "KeyS") {
        keyState.s = true;
        direction = "DOWN";
    } else if (event.code === "ArrowUp") {
        keyState.up = true;
        direction = "UP";
    } else if (event.code === "ArrowDown") {
        keyState.down = true;
        direction = "DOWN";
    }

    if (direction) {
        socket.send(JSON.stringify({ action: "move", player_id: playerId, direction: direction }));
    }
}

function keyUpHandlerOnline(event, socket) {
    if (["KeyW", "KeyS", "ArrowUp", "ArrowDown"].includes(event.code)) event.preventDefault();
    if (socket.readyState !== WebSocket.OPEN || !playerId) return;  // Ensure playerId exists

    let direction = "STOP";

    if (event.code === "KeyW") {
        keyState.w = false;
        if (keyState.down || keyState.s) direction = "DOWN";
    } else if (event.code === "KeyS") {
        keyState.s = false;
        if (keyState.w) direction = "UP";
    } else if (event.code === "ArrowUp") {
        keyState.up = false;
        if (keyState.down || keyState.s) direction = "DOWN";
    } else if (event.code === "ArrowDown") {
        keyState.down = false;
        if (keyState.up || keyState.w) direction = "UP";
    }

    socket.send(JSON.stringify({ action: "move", player_id: playerId, direction: direction }));
}
