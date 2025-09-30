import { WorkflowEvent } from "@llamaindex/ui";

export type WordStreamData = { word: string };

export function isWordStream(
  e: WorkflowEvent,
): e is { type: string; data: WordStreamData } {
  return e.type.endsWith(".WordStreamEvent");
}

export function isFullTextStopEvent(
  e: WorkflowEvent,
): e is { type: string; data: { text?: string } } {
  return e.type.endsWith(".FullTextStopEvent");
}
