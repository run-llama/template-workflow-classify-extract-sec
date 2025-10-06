import { useState } from "react";
import { useWorkflowRun, useWorkflowHandler } from "@llamaindex/ui";

export default function Home() {
  const [handlerId, setHandlerId] = useState<string | null>(null);
  const run = useWorkflowRun();
  const handler = useWorkflowHandler(handlerId ?? "");

  const result = handler.events.find((e) => e.type.endsWith(".StopEvent")) as
    | { type: string; data: { result?: string } }
    | undefined;

  return (
    <div className="relative min-h-screen flex items-center justify-center p-6">
      <div className="max-w-2xl text-center text-black/80 dark:text-white/80 flex flex-col gap-4">
        <p className="text-lg">
          This is a minimal UI starter. Click the button to run the backend
          workflow and display its result.
        </p>
        <div className="flex items-center justify-center gap-3">
          <button
            type="button"
            disabled={run.isCreating}
            onClick={() =>
              run
                .runWorkflow("default", {})
                .then((h) => setHandlerId(h.handler_id))
            }
            className="inline-flex items-center justify-center rounded-xl border px-6 py-3 text-sm font-semibold shadow-sm border-black/10 bg-black/5 text-black hover:bg-black/10 dark:border-white/10 dark:bg-white/10 dark:text-white"
          >
            Run Workflow
          </button>
        </div>
        <div className="text-sm">
          {handlerId && (
            <div>
              Handler: <code>{handlerId}</code>
            </div>
          )}
          {result?.data?.result && (
            <div className="mt-2">
              Result: <code>{result.data.result}</code>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
