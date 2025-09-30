import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useWorkflowHandler, useWorkflowRun } from "@llamaindex/ui";
import { CANCEL_EVENT, isSnapshot, isTick, TickData } from "./events";
import { useComponentWorkflow, useExistingWorkflow } from "../../hooks";
import { Sparkline } from "@/components/sparkline";
import HandlerId from "@/components/handler-id";

export type GetOrCreateHandlerIdResult = {
  handler: ReturnType<typeof useWorkflowHandler>;
  recreateHandler: () => void;
};

export default function SnapshotQueryPage() {
  // Create a new handler on page load
  const { handler, recreateHandler, failedToCreate } = useExistingWorkflow({
    workflowName: "snapshot_query",
    stopEvent: CANCEL_EVENT,
  });

  const maxTicks = 10;

  useEffect(() => {
    if (handler.handler?.handler_id) {
      handler.sendEvent({
        type: "app.state_query.workflow.ProbeEvent",
        data: {
          n_ticks: maxTicks,
        },
      });
    }
  }, [handler?.handler?.handler_id]);

  const snapshot = useMemo(() => {
    const snapshot = handler.events
      .filter(isSnapshot)
      .map((e) => e.data)
      .slice(-1)[0];
    return snapshot;
  }, [handler.events]);

  const ticks: TickData[] = useMemo(() => {
    const snapshotTicks = snapshot?.recent_ticks ?? [];
    const eventTicks = handler.events.filter(isTick).map((e) => e.data);
    return snapshotTicks.concat(eventTicks);
  }, [snapshot?.recent_ticks, handler.events]);

  const tickValues = useMemo(() => {
    return ticks.map((t) => t.value);
  }, [ticks]);

  return (
    <div className="min-h-dvh aurora-container">
      <div className="relative z-10 mx-auto max-w-3xl px-4 py-8 sm:py-12">
        <header className="mb-6">
          <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight">
            Query a Workflow's State
          </h1>
          <p className="mt-2">
            While this demo is streaming, it reloads the chart history from the
            workflow state on load. To do this, the client sends a{" "}
            <code>ProbeEvent</code> event, and the workflow responds with a{" "}
            <code>SnapshotEvent</code>. If you reload or navigate back, the
            history will be restored.
          </p>

          <HandlerId handler={handler} failedToCreate={failedToCreate} />
        </header>
        <section>
          <Sparkline
            key={handler.handler?.handler_id}
            values={tickValues}
            height={320}
            maxVisible={maxTicks}
            color="#0891b2"
            fixedRange={[0, 1]}
          />
        </section>
        <div className="mt-6">
          <button
            className="inline-flex items-center rounded-md border px-3 py-1.5 text-sm bg-white/70 dark:bg-zinc-900/50 hover:bg-white/90 dark:hover:bg-zinc-900/70 border-zinc-200/70 dark:border-zinc-800/70 cursor-pointer"
            onClick={() => {
              recreateHandler();
            }}
          >
            New handler
          </button>
        </div>
      </div>
    </div>
  );
}
