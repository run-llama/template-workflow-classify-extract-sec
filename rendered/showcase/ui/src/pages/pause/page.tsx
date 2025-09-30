import HandlerId from "@/components/handler-id";
import { useEffect, useMemo } from "react";
import { useExistingWorkflow } from "../../hooks";
import {
  isRoomStateEvent,
  isStopEvent,
  isGameSnapshot,
  PROBE_EVENT,
} from "./events";
import { useWorkflowHandler, WorkflowEvent } from "@llamaindex/ui";

interface GameState {
  currentRoom: string | null;
  inputPrompt: string | null;
  validExits: ("north" | "east" | "south" | "west")[];
  result: string | null;
}

const emptyGameState: GameState = {
  currentRoom: null,
  inputPrompt: null,
  validExits: [],
  result: null,
};

function reduceGameState(state: GameState, event: WorkflowEvent): GameState {
  if (isGameSnapshot(event)) {
    // Snapshot restores full state (used on page reload)
    const isComplete =
      !event.data.awaiting_input && event.data.current_room === "exit";
    return {
      currentRoom: event.data.current_description,
      inputPrompt: event.data.awaiting_input ? event.data.input_prompt : null,
      validExits: event.data.valid_exits,
      result: isComplete
        ? `Congratulations! You escaped the maze in ${event.data.moves} moves!`
        : null,
    };
  } else if (isRoomStateEvent(event)) {
    return {
      currentRoom: event.data.description,
      inputPrompt: event.data.prompt,
      validExits: event.data.exits,
      result: null,
    };
  } else if (isStopEvent(event)) {
    return {
      ...state,
      inputPrompt: null,
      result: event.data.game_over,
    };
  }
  return state;
}

function getGameState(
  handler: ReturnType<typeof useWorkflowHandler>,
): GameState {
  const events = handler.events;
  const state = useMemo(
    () => events.reduce(reduceGameState, emptyGameState),
    [events],
  );
  return state;
}

export default function PausePage() {
  const { handler, recreateHandler, failedToCreate } = useExistingWorkflow({
    workflowName: "pause",
  });

  // Send probe event when handler loads
  useEffect(() => {
    if (handler.handler?.handler_id) {
      handler.sendEvent(PROBE_EVENT);
    }
  }, [handler.handler?.handler_id]);

  const gameState = getGameState(handler);

  const sendMove = (direction: string) => {
    handler.sendEvent({
      type: "app.pause.workflow.PlayerMoveEvent",
      data: { direction },
    });
  };

  const isComplete = !!gameState.result;

  return (
    <div className="min-h-dvh aurora-container">
      <div className="relative z-10 mx-auto max-w-4xl px-4 py-8 sm:py-12">
        <header className="mb-6">
          <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight">
            Maze Game - Pause for Input
          </h1>
          <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
            Navigate through the maze. State persists - reload anytime.
          </p>
          {handler && (
            <HandlerId handler={handler} failedToCreate={failedToCreate} />
          )}
        </header>

        {/* Retro Terminal Display */}
        <section className="rounded-lg border-2 border-cyan-500/30 bg-black/90 backdrop-blur p-6 shadow-2xl font-mono text-cyan-400">
          <div className="mb-4 pb-3 border-b border-cyan-500/30">
            <div className="flex items-center gap-2">
              <span className="text-xs">█</span>
              <span className="text-xs uppercase tracking-wider">
                Adventure System v1.0
              </span>
            </div>
          </div>

          {/* Current Room */}
          <div className="min-h-[50px] space-y-4">
            {gameState.currentRoom && (
              <div className="space-y-2">
                <p className="text-sm leading-relaxed">
                  {gameState.currentRoom}
                </p>
              </div>
            )}

            {/* Result */}
            {gameState.result && (
              <div className="space-y-2">
                <p className="text-yellow-400 text-sm">{gameState.result}</p>
                <p className="text-xs text-cyan-500 animate-pulse">
                  &gt; Game Complete
                </p>
              </div>
            )}

            {!gameState.currentRoom && !gameState.result && (
              <div className="text-xs text-cyan-500/50 animate-pulse">
                &gt; Initializing...
              </div>
            )}
          </div>

          {/* Navigation Controls */}
          {gameState.inputPrompt && !isComplete && (
            <div className="mt-6 pt-4 border-t border-cyan-500/30">
              <div className="flex items-center justify-center">
                <NavButton
                  directions={gameState.validExits}
                  onClick={sendMove}
                />
              </div>
            </div>
          )}
        </section>

        <div className="mt-6">
          <button
            className="inline-flex items-center rounded-md border px-3 py-1.5 text-sm bg-white/70 dark:bg-zinc-900/50 hover:bg-white/90 dark:hover:bg-zinc-900/70 border-zinc-200/70 dark:border-zinc-800/70 cursor-pointer"
            onClick={() => recreateHandler()}
          >
            New Game
          </button>
        </div>
      </div>
    </div>
  );
}

const NavButton = ({
  directions,
  onClick,
}: {
  directions: ("north" | "east" | "south" | "west")[];
  onClick: (direction: "north" | "east" | "south" | "west") => void;
}) => {
  return (
    <div className="grid grid-cols-3 grid-rows-3 gap-2">
      {/* Top row - North */}
      <div></div>
      <button
        onClick={() => onClick("north")}
        disabled={!directions.includes("north")}
        className="w-12 h-12 flex items-center justify-center rounded border-2 border-cyan-500 bg-cyan-950 hover:bg-cyan-900 disabled:border-cyan-900/30 disabled:bg-black disabled:cursor-not-allowed cursor-pointer text-cyan-400 disabled:text-cyan-900/50 transition-colors text-xl"
        aria-label="Go North"
      >
        ↑
      </button>
      <div></div>

      {/* Middle row - West and East */}
      <button
        onClick={() => onClick("west")}
        disabled={!directions.includes("west")}
        className="w-12 h-12 flex items-center justify-center rounded border-2 border-cyan-500 bg-cyan-950 hover:bg-cyan-900 disabled:border-cyan-900/30 disabled:bg-black disabled:cursor-not-allowed cursor-pointer text-cyan-400 disabled:text-cyan-900/50 transition-colors text-xl"
        aria-label="Go West"
      >
        ←
      </button>
      <div className="w-12 h-12 flex items-center justify-center text-cyan-500/20 text-2xl">
        ✦
      </div>
      <button
        onClick={() => onClick("east")}
        disabled={!directions.includes("east")}
        className="w-12 h-12 flex items-center justify-center rounded border-2 border-cyan-500 bg-cyan-950 hover:bg-cyan-900 disabled:border-cyan-900/30 disabled:bg-black disabled:cursor-not-allowed cursor-pointer text-cyan-400 disabled:text-cyan-900/50 transition-colors text-xl"
        aria-label="Go East"
      >
        →
      </button>

      {/* Bottom row - South */}
      <div></div>
      <button
        onClick={() => onClick("south")}
        disabled={!directions.includes("south")}
        className="w-12 h-12 flex items-center justify-center rounded border-2 border-cyan-500 bg-cyan-950 hover:bg-cyan-900 disabled:border-cyan-900/30 disabled:bg-black disabled:cursor-not-allowed cursor-pointer text-cyan-400 disabled:text-cyan-900/50 transition-colors text-xl"
        aria-label="Go South"
      >
        ↓
      </button>
      <div></div>
    </div>
  );
};
