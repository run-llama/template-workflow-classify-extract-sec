import {
  useWorkflowHandler,
  useWorkflowRun,
  useHandlerStore,
} from "@llamaindex/ui";
import { useEffect, useRef, useState } from "react";
import { INDEX_NAME } from "./config";
import { createQueryConversationHistoryEvent } from "./events";

/**
 * Creates a new chat conversation if no handlerId is provided
 */
export function useChatWorkflowHandler({
  handlerId,
  onHandlerCreated,
}: {
  handlerId?: string;
  onHandlerCreated?: (handlerId: string) => void;
}): ReturnType<typeof useWorkflowHandler> {
  const create = useWorkflowRun();
  const isQueryingWorkflow = useRef(false);
  const [thisHandlerId, setThisHandlerId] = useState<string | undefined>(
    handlerId,
  );
  const workflowHandler = useWorkflowHandler(thisHandlerId ?? "", true);
  const store = useHandlerStore();

  const createHandler = async () => {
    if (isQueryingWorkflow.current) return;
    isQueryingWorkflow.current = true;
    try {
      const handler = await create.runWorkflow("chat", {
        index_name: INDEX_NAME,
      });
      setThisHandlerId(handler.handler_id);
      onHandlerCreated?.(handler.handler_id);
    } finally {
      isQueryingWorkflow.current = false;
    }
  };
  const replayHandler = async () => {
    if (isQueryingWorkflow.current) return;
    isQueryingWorkflow.current = true;
    try {
      await workflowHandler.sendEvent(createQueryConversationHistoryEvent());
    } finally {
      isQueryingWorkflow.current = false;
    }
  };

  useEffect(() => {
    if (!thisHandlerId) {
      createHandler();
    } else {
      // kick it. This is a temp workaround for a bug
      store.sync().then(() => {
        store.subscribe(thisHandlerId);
      });
    }
  }, [thisHandlerId]);

  useEffect(() => {
    if (thisHandlerId && workflowHandler.isStreaming) {
      replayHandler();
    }
  }, [thisHandlerId, workflowHandler.isStreaming]);

  return workflowHandler;
}
