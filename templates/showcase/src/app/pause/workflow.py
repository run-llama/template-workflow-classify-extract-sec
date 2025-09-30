from pydantic import BaseModel, Field
from workflows import Context, Workflow, step
from workflows.events import (
    Event,
    HumanResponseEvent,
    InputRequiredEvent,
    StartEvent,
    StopEvent,
)


# Custom Events
class RoomStateEvent(InputRequiredEvent):
    """Describes the current room and prompts for player input."""

    description: str
    exits: list[str]
    prompt: str


class ProbeEvent(HumanResponseEvent):
    """Request current game state."""

    pass


class GameSnapshotEvent(Event):
    """Response containing current game state for restoration."""

    current_room: str
    current_description: str
    valid_exits: list[str]
    awaiting_input: bool
    input_prompt: str | None
    moves: int


class PlayerMoveEvent(HumanResponseEvent):
    """Player's chosen direction."""

    direction: str


# Game State
class GameState(BaseModel):
    """Tracks game progress."""

    current_room: str = "start"
    history: list[str] = Field(default_factory=list)
    moves: int = 0


class GameOverEvent(StopEvent):
    """Ends the game."""

    game_over: str


# Maze Definition
MAZE = {
    "start": {
        "description": "You are at the entrance of a mysterious maze. Torches flicker on the walls.",
        "exits": {"north": "hallway", "east": "dark_room"},
    },
    "hallway": {
        "description": "A long hallway stretches before you. You hear dripping water.",
        "exits": {"south": "start", "east": "treasure_room", "north": "dead_end"},
    },
    "dark_room": {
        "description": "It's very dark here. You can barely see the exits.",
        "exits": {"west": "start", "north": "treasure_room"},
    },
    "treasure_room": {
        "description": "A room filled with ancient artifacts and gold coins!",
        "exits": {"west": "hallway", "south": "dark_room", "north": "exit"},
    },
    "dead_end": {
        "description": "You hit a dead end. The wall is solid stone.",
        "exits": {"south": "hallway"},
    },
    "exit": {
        "description": "You see daylight! You've found the exit!",
        "exits": {},
    },
}


class MazeGameWorkflow(Workflow):
    @step
    async def start_game(
        self, ev: StartEvent, ctx: Context[GameState]
    ) -> RoomStateEvent:
        """Initialize the game."""
        async with ctx.store.edit_state() as state:
            state.current_room = "start"
            state.moves = 0

        return await self._describe_room(ctx, "start")

    @step
    async def handle_move(
        self, ev: PlayerMoveEvent, ctx: Context[GameState]
    ) -> RoomStateEvent | GameOverEvent:
        """Process player's move and show the new room."""
        state = await ctx.store.get_state()
        current_room = MAZE[state.current_room]
        direction = ev.direction.lower().strip()

        # Check if direction is valid
        if direction not in current_room["exits"]:
            # Invalid move - stay in same room
            async with ctx.store.edit_state() as state:
                state.history.append(f"You can't go {direction} from here. Try again.")

            return await self._describe_room(ctx, state.current_room)

        # Valid move - go to new room
        new_room = current_room["exits"][direction]
        async with ctx.store.edit_state() as state:
            state.current_room = new_room
            state.moves += 1

        # Check if player reached the exit
        if new_room == "exit":
            return GameOverEvent(
                game_over=f"Congratulations! You escaped the maze in {state.moves} moves!"
            )

        return await self._describe_room(ctx, new_room)

    @step
    async def probe(self, ev: ProbeEvent, ctx: Context[GameState]) -> None:
        """Respond to probe events with current state snapshot."""
        state = await ctx.store.get_state()
        current_room = MAZE[state.current_room]

        # Check if at exit
        is_at_exit = state.current_room == "exit"

        ctx.write_event_to_stream(
            GameSnapshotEvent(
                current_room=state.current_room,
                current_description=current_room["description"],
                valid_exits=list(current_room["exits"].keys()),
                awaiting_input=not is_at_exit,
                input_prompt=(
                    f"Which way do you want to go? ({', '.join(current_room['exits'].keys())})"
                    if not is_at_exit
                    else None
                ),
                moves=state.moves,
            )
        )

    async def _describe_room(
        self, ctx: Context[GameState], room_id: str
    ) -> RoomStateEvent:
        """Helper to describe a room and add to history."""
        room = MAZE[room_id]
        description = room["description"]
        exits = list(room["exits"].keys())
        exits_str = ", ".join(exits)
        prompt = f"Which way do you want to go? ({exits_str})"

        async with ctx.store.edit_state() as state:
            state.history.append(description)

        event = RoomStateEvent(description=description, exits=exits, prompt=prompt)
        ctx.write_event_to_stream(event)
        return event


pause_workflow = MazeGameWorkflow(timeout=None)
