import { WorkflowEvent } from "@llamaindex/ui";

export function createQueryConversationHistoryEvent(): WorkflowEvent {
  return {
    data: {},
    type: "document_qa.qa_workflows.QueryConversationHistoryEvent",
  };
}

export function createHumanResponseEvent(response: string): WorkflowEvent {
  return {
    data: { _data: { response } },
    type: "document_qa.qa_workflows.HumanResponseEvent",
  };
}
