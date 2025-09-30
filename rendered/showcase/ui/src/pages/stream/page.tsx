import { useMemo } from "react";
import { isWordStream, isFullTextStopEvent } from "./events";
import HandlerId from "@/components/handler-id";
import { useComponentWorkflow } from "../../hooks";

export default function StreamPage() {
  const { handler, recreateHandler, failedToCreate } = useComponentWorkflow({
    workflowName: "stream",
  });

  // Construct text from streamed events, or use final result if available
  const { text, isComplete } = useMemo(() => {
    const events = handler.events;

    // Check if we have a final result
    const stopEvent = events.find(isFullTextStopEvent);
    if (stopEvent?.data?.text) {
      return { text: stopEvent.data.text, isComplete: true };
    }

    // Otherwise, construct from streamed words
    const streamedWords = events.filter(isWordStream).map((e) => e.data.word);
    return { text: streamedWords.join(" "), isComplete: false };
  }, [handler.events]);

  return (
    <div className="min-h-dvh aurora-container">
      <div className="relative z-10 mx-auto max-w-5xl px-4 py-8 sm:py-12">
        <header className="mb-6">
          <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight">
            Streaming
          </h1>
          <p className="mt-2">
            Watch text stream word by word from the workflow. Words are
            constructed on the client until the final result arrives.
          </p>
          {handler && (
            <HandlerId handler={handler} failedToCreate={failedToCreate} />
          )}
        </header>

        <section className="rounded-lg border border-zinc-200/70 dark:border-zinc-800/70 bg-white/50 dark:bg-zinc-900/40 backdrop-blur p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium">Streamed Text</h2>
            <div className="text-xs text-zinc-500">
              {!isComplete && <span>Streaming...</span>}
            </div>
          </div>
          <div className="text-base leading-relaxed">
            {text ? (
              text
            ) : (
              <span className="text-zinc-400">Waiting for stream...</span>
            )}
          </div>
        </section>

        <div className="mt-6">
          <button
            className="inline-flex items-center rounded-md border px-3 py-1.5 text-sm bg-white/70 dark:bg-zinc-900/50 hover:bg-white/90 dark:hover:bg-zinc-900/70 border-zinc-200/70 dark:border-zinc-800/70 cursor-pointer"
            onClick={async () => {
              recreateHandler();
            }}
          >
            Stream Again
          </button>
        </div>
      </div>
    </div>
  );
}
