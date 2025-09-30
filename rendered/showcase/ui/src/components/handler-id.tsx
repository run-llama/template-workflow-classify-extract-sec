import { useWorkflowHandler } from "@llamaindex/ui";

export default function HandlerId({
  handler,
  failedToCreate,
}: {
  handler: ReturnType<typeof useWorkflowHandler>;
  failedToCreate: Error | null;
}) {
  const isComplete = handler.handler?.status === "complete";
  const isError = handler.handler?.status === "failed";

  return (
    <div className="mt-3 text-xs text-zinc-600 dark:text-zinc-400">
      {handler.handler?.handler_id ? (
        <span>
          Handler: <code>{handler.handler?.handler_id}</code>{" "}
          {isComplete ? (
            <span className="text-green-500 ml-1">Complete</span>
          ) : isError ? (
            <span className="text-red-500 ml-1">Error</span>
          ) : (
            <span className="ml-1">Running</span>
          )}
        </span>
      ) : failedToCreate ? (
        <span className="text-red-500"> Error: {failedToCreate.message}</span>
      ) : (
        <span>Starting…</span>
      )}
    </div>
  );
}
