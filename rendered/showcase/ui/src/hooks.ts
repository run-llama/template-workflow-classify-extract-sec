import {
  useWorkflowHandler,
  useWorkflowHandlerList,
  useWorkflowRun,
  WorkflowEvent,
} from "@llamaindex/ui";
import { useEffect, useRef, useState } from "react";

export type GetOrCreateHandlerIdResult = {
  handlerId: string | null;
  handler: ReturnType<typeof useWorkflowHandler>;
  recreateHandler: () => void;
  failedToCreate: Error | null;
};

/**
 * retrieves any existing handler for the specified workflow name and re-uses it
 */
export function useExistingWorkflow({
  workflowName,
  stopEvent,
}: {
  workflowName: string;
  stopEvent?: WorkflowEvent;
}): GetOrCreateHandlerIdResult {
  const available = useWorkflowHandlerList(workflowName);
  const run = useWorkflowRun();
  const [isInitialized, setIsInitialized] = useState(false);
  const [handlerId, setHandlerId] = useState<string | null>(null);
  const handler = useWorkflowHandler(handlerId ?? "", true);
  const lastHandlerId = useRef<string | null>(null);
  const [failedToCreate, setFailedToCreate] = useState<Error | null>(null);
  useEffect(() => {
    if (handlerId) {
      lastHandlerId.current = handlerId;
    }
  }, [handlerId]);

  // first, fetch a handler from the existing on load.
  useEffect(() => {
    if (!isInitialized && !available.loading) {
      const availableHandlerId = available.handlers.find(
        (h) => h.status === "running",
      )?.handler_id;
      setHandlerId(availableHandlerId ?? null);
      setIsInitialized(true);
    }
  }, [isInitialized, available.loading]);

  // create a new handler if one doesn't exist.
  useEffect(() => {
    if (!handlerId && !run.isCreating && isInitialized && !failedToCreate) {
      run
        .runWorkflow(workflowName, {})
        .then((handler) => {
          setHandlerId(handler.handler_id);
        })
        .catch((error) => {
          console.error(error);
          setFailedToCreate(error);
        });
    }
  }, [handlerId, isInitialized, run.isCreating]);

  // cancel old handlers when a new one is created.
  useEffect(() => {
    if (
      !handlerId &&
      lastHandlerId.current &&
      handlerId !== lastHandlerId.current &&
      stopEvent
    ) {
      handler.sendEvent(stopEvent);
    }
  }, [handlerId, lastHandlerId.current]);

  return {
    handlerId: handlerId,
    handler: handler,
    recreateHandler: () => {
      setHandlerId(null);
      setFailedToCreate(null);
    },
    failedToCreate: failedToCreate ?? null,
  };
}

/**
 * Creates a workflow handler for the lifetime of the component.
 * Sends the specified stop event to the handler when the page is unloaded.
 * */
export function useComponentWorkflow({
  workflowName,
  stopEvent,
}: {
  workflowName: string;
  stopEvent?: WorkflowEvent;
}): GetOrCreateHandlerIdResult {
  const run = useWorkflowRun();
  const isCreating = useRef(false);
  const [handlerId, setHandlerId] = useState<string | null>(null);
  const handler = useWorkflowHandler(handlerId ?? "", true);
  const [failedToCreate, setFailedToCreate] = useState<Error | null>(null);
  useEffect(() => {
    if (
      !handlerId &&
      !run.isCreating &&
      !isCreating.current &&
      !failedToCreate
    ) {
      isCreating.current = true;

      run
        .runWorkflow(workflowName, {})
        .then((handler) => {
          setHandlerId(handler.handler_id);
        })
        .catch((error) => {
          console.error(error);
          setFailedToCreate(error);
        })
        .finally(() => {
          isCreating.current = false;
        });
    }
  }, [handlerId, run.isCreating]);
  useEffect(() => {
    return () => {
      if (handlerId && stopEvent) {
        handler.sendEvent(stopEvent);
      }
    };
  }, [handlerId]);
  return {
    handlerId: handlerId,
    handler: handler,
    recreateHandler: () => {
      if (stopEvent) {
        handler.sendEvent(stopEvent);
      }
      setFailedToCreate(null);
      setHandlerId(null);
    },
    failedToCreate: failedToCreate ?? null,
  };
}
