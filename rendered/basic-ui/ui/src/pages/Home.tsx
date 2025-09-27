import { useState } from "react";
import {
  type WorkflowEvent,
  useWorkflowHandler,
  useWorkflowRun,
} from "@llamaindex/ui";

export default function Home() {
  const [taskId, setTaskId] = useState<string | null>(null);
  const createHandler = useWorkflowRun();
  return (
    <div className="aurora-container relative min-h-screen overflow-hidden bg-background text-foreground">
      <main className="relative mx-auto flex min-h-screen max-w-2xl px-6 flex-col gap-4 items-center justify-center my-12">
        <div className="text-center mb-4 text-black/80 dark:text-white/80 text-lg">
          This is a basic starter app for LlamaDeploy. It's running a simple
          Human-in-the-loop workflow on the backend, and vite with react on the
          frontend with llama-ui to call the workflow. Customize this app with
          your own workflow and UI.
        </div>
        <div className="flex flex-row gap-4 items-start justify-center w-full">
          <HandlerOutput handlerId={taskId} />
          <RunButton
            disabled={createHandler.isCreating}
            onClick={() =>
              createHandler
                .runWorkflow("default", {
                  message: `${new Date().toLocaleTimeString()} PING`,
                })
                .then((task) => setTaskId(task.handler_id))
            }
          >
            <GreenDot />
            Run
          </RunButton>
        </div>
      </main>
    </div>
  );
}

const GreenDot = () => {
  return (
    <span className="mr-2 size-2 rounded-full bg-emerald-500/80 shadow-[0_0_20px_2px_rgba(16,185,129,0.35)] transition group-hover:bg-emerald-400/90"></span>
  );
};

function RunButton({
  disabled,
  children,
  onClick,
}: {
  disabled: boolean;
  children: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className="group inline-flex items-center justify-center rounded-xl border px-6 py-3 text-sm font-semibold shadow-sm backdrop-blur transition active:scale-[.99]
      border-black/10 bg-black/5 text-black hover:bg-black/10 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-black/20
      dark:border-white/10 dark:bg-white/10 dark:text-white dark:hover:bg-white/15 dark:focus:ring-white/30 cursor-pointer"
    >
      {children}
    </button>
  );
}

type PongEvent = { type: `${string}.PongEvent`; data: { message: string } };
type PauseEvent = { type: `${string}.PauseEvent`; data: { timestamp: string } };

function isPongEvent(event: WorkflowEvent): event is PongEvent {
  return event.type.endsWith(".PongEvent");
}
function isPauseEvent(event: WorkflowEvent): event is PauseEvent {
  return event.type.endsWith(".PauseEvent");
}

function HandlerOutput({ handlerId }: { handlerId: string | null }) {
  // stream events and result from the workflow
  const handler = useWorkflowHandler(handlerId ?? "");

  // read workflow events here
  const pongsOrResume = handler.events.filter(
    (event) => isPongEvent(event) || isPauseEvent(event),
  ) as (PongEvent | PauseEvent)[];
  const completed = handler.events.find((event) =>
    event.type.endsWith(".WorkflowCompletedEvent"),
  ) as { type: string; data: { timestamp: string } } | undefined;

  return (
    <div className="flex flex-col gap-4 w-full min-h-60 items-center">
      <Output>{completed ? completed.data.timestamp : "Running... "}</Output>
      {pongsOrResume.map((pong, index) => (
        <span
          className="inline-flex items-center px-2 py-0.5 text-xs font-medium bg-black/3 
          dark:bg-white/2 text-black/60 dark:text-white/60 rounded border border-black/5 
          dark:border-white/5 backdrop-blur-sm"
          key={index}
          style={{
            animation: "fade-in-left 80ms ease-out both",
            willChange: "opacity, transform",
          }}
        >
          {isPongEvent(pong) ? pong.data.message : pong.data.timestamp}
          {isPauseEvent(pong) &&
            index === pongsOrResume.length - 1 &&
            !completed && (
              <button
                onClick={() =>
                  handler.sendEvent({
                    type: "app.workflow.ResumeEvent",
                    data: { should_continue: true },
                  })
                }
                className="ml-2 px-2 py-0.5 bg-black/10 hover:bg-black/20 dark:bg-white/10 dark:hover:bg-white/20 
              text-black/80 dark:text-white/80 text-xs rounded border border-black/10 dark:border-white/10"
              >
                Resume?
              </button>
            )}
        </span>
      ))}
      {!completed && pongsOrResume.length > 0 && (
        <button
          onClick={() =>
            handler.sendEvent({
              type: "app.workflow.ResumeEvent",
              data: { should_continue: false },
            })
          }
          className="ml-2 px-2 py-0.5 bg-black/10 hover:bg-black/20 dark:bg-white/10 dark:hover:bg-white/20 
              text-black/80 dark:text-white/80 text-xs rounded border border-black/10 dark:border-white/10"
        >
          Stop
        </button>
      )}
    </div>
  );
}

function Output({ children }: { children: React.ReactNode }) {
  return (
    <div
      aria-live="polite"
      className="w-full rounded-xl border bg-black/5 p-4 text-left shadow-[inset_0_1px_0_0_rgba(255,255,255,0.06)]
      border-black/10 dark:border-white/10 dark:bg-white/5"
    >
      <pre className="whitespace-pre-wrap break-words font-mono text-xs text-black/80 dark:text-white/80">
        {children}
      </pre>
    </div>
  );
}
