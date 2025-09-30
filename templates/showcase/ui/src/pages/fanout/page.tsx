import { useEffect, useMemo, useState } from "react";
import { useWorkflowRun, useWorkflowHandler } from "@llamaindex/ui";
import {
  type UnknownEvent,
  isBatchPlanned,
  isTaskCompleted,
  isTaskProgress,
  isTaskStarted,
} from "./events";
import HandlerId from "@/components/handler-id";
import { useComponentWorkflow } from "@/hooks";

type TaskState = "pending" | "started" | "progressing" | "complete";

type Item = {
  id: number;
  state: TaskState;
  percent: number;
  startedAtMs?: number;
  finishedAtMs?: number;
  durationMs?: number;
};

export default function FanOutPage() {
  const { handler, recreateHandler, failedToCreate } = useComponentWorkflow({
    workflowName: "fanout",
  });

  const items = useMemo((): Item[] => {
    const map = new Map<number, Item>();
    for (const e of handler.events as UnknownEvent[]) {
      if (isBatchPlanned(e)) {
        const ids = e.data.task_ids;
        for (const id of ids) {
          if (!map.has(id)) map.set(id, { id, state: "pending", percent: 0 });
        }
      } else if (isTaskStarted(e)) {
        const { task_id, started_at_ms } = e.data;
        const prev = map.get(task_id) || {
          id: task_id,
          state: "pending",
          percent: 0,
        };
        map.set(task_id, {
          ...prev,
          state: "started",
          startedAtMs: started_at_ms,
        });
      } else if (isTaskProgress(e)) {
        const { task_id, percent } = e.data;
        const prev = map.get(task_id) || {
          id: task_id,
          state: "pending",
          percent: 0,
        };
        map.set(task_id, {
          ...prev,
          state: percent < 100 ? "progressing" : "complete",
          percent,
        });
      } else if (isTaskCompleted(e)) {
        const { task_id, started_at_ms, finished_at_ms, duration_ms } = e.data;
        const prev = map.get(task_id) || {
          id: task_id,
          state: "pending",
          percent: 0,
        };
        map.set(task_id, {
          ...prev,
          state: "complete",
          percent: 100,
          startedAtMs: started_at_ms ?? prev.startedAtMs,
          finishedAtMs: finished_at_ms,
          durationMs: duration_ms,
        });
      }
    }
    return Array.from(map.values()).sort((a, b) => a.id - b.id);
  }, [handler.events]);

  return (
    <div className="min-h-dvh aurora-container">
      <div className="relative z-10 mx-auto max-w-5xl px-4 py-8 sm:py-12">
        <header className="mb-6">
          <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight">
            Parallel Extraction (Fan-Out)
          </h1>
          <p className="mt-2">
            Easily create and observe parallel tasks. Fire multiple events with{" "}
            <code>send_event</code>, and limit concurrency with{" "}
            <code>num_workers</code>.
          </p>
          {handler && (
            <HandlerId handler={handler} failedToCreate={failedToCreate} />
          )}
        </header>

        <section>
          <ul className="grid sm:grid-cols-2 gap-4">
            {items.map((i) => (
              <li
                key={i.id}
                className="rounded-lg border border-zinc-200/70 dark:border-zinc-800/70 bg-white/50 dark:bg-zinc-900/40 backdrop-blur p-4"
              >
                <div className="flex items-center justify-between">
                  <div className="text-sm font-medium">Task #{i.id}</div>
                  <div className="text-xs text-zinc-500">
                    {i.state === "pending" && "Pending"}
                    {i.state === "started" && "Started"}
                    {i.state === "progressing" && `${i.percent}%`}
                  </div>
                </div>
                <div className="mt-2 h-2 w-full rounded bg-zinc-200/60 dark:bg-zinc-800/60 overflow-hidden">
                  <div
                    className="h-full rounded bg-gradient-to-r from-sky-500 to-cyan-400 transition-all"
                    style={{ width: `${i.percent}%` }}
                  />
                </div>
                <div className="mt-2 text-xs text-zinc-600 dark:text-zinc-400">
                  {typeof i.durationMs === "number" ? (
                    <span>duration: {(i.durationMs / 1000).toFixed(2)}s</span>
                  ) : i.state === "pending" ? (
                    <span>awaiting start…</span>
                  ) : i.state === "progressing" ? (
                    <span>in progress…</span>
                  ) : (
                    <span>complete</span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </section>

        <div className="mt-6">
          <button
            className="inline-flex items-center rounded-md border px-3 py-1.5 text-sm bg-white/70 dark:bg-zinc-900/50 hover:bg-white/90 dark:hover:bg-zinc-900/70 border-zinc-200/70 dark:border-zinc-800/70 cursor-pointer"
            onClick={async () => {
              recreateHandler();
            }}
          >
            Run again
          </button>
        </div>
      </div>
    </div>
  );
}
