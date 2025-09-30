import { WorkflowEvent } from "@llamaindex/ui";

export type TickData = { value: number; timestamp_ms: number };
export type ProbeData = { requested_at_ms: number };
export type SnapshotData = {
  requested_at_ms: number;
  recent_ticks: TickData[];
  scale: number;
};

export function isTick(
  e: WorkflowEvent,
): e is { type: string; data: TickData } {
  return e.type.endsWith(".TickEvent");
}

export function isSnapshot(
  e: WorkflowEvent,
): e is { type: string; data: SnapshotData } {
  return e.type.endsWith(".SnapshotEvent");
}

export const CANCEL_EVENT: WorkflowEvent = {
  type: "app.state_query.workflow.CancelEvent",
};
