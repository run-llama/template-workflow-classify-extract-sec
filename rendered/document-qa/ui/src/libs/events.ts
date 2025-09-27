import { WorkflowEvent } from "@llamaindex/ui";

export function createQueryConversationHistoryEvent(): WorkflowEvent {
  return {
    data: {},
    type: "test_proj.qa_workflows.QueryConversationHistoryEvent",
  };
}

export function createHumanResponseEvent(response: string): WorkflowEvent {
  return {
    data: { _data: { response } },
    type: "test_proj.qa_workflows.HumanResponseEvent",
  };
}
