import ChatBot from "../components/ChatBot";
import { useWorkflowHandlerList, WorkflowTrigger } from "@llamaindex/ui";
import { APP_TITLE, INDEX_NAME } from "../libs/config";
import { useChatHistory } from "@/libs/useChatHistory";
import Sidebar from "@/components/Sidebar";
import { Loader } from "lucide-react";

export default function Home() {
  const chatHistory = useChatHistory();
  const handlers = useWorkflowHandlerList("upload");
  const activeHandlers = handlers.handlers.filter(
    (h) => h.status === "running" && h.workflowName === "upload",
  );
  const anyActiveHandlers = activeHandlers.length > 0;

  return (
    <div className="min-h-screen bg-background">
      <div className="flex h-screen">
        <Sidebar chatHistory={chatHistory} />
        <div className="flex-1 flex flex-col">
          {/* Simplified header with upload functionality */}
          <header className="flex items-center justify-between p-4 border-b bg-card">
            <div>
              <h1 className="text-xl font-semibold text-foreground">
                {APP_TITLE}
              </h1>
              <p className="text-sm text-muted-foreground">
                Upload documents and ask questions about them
              </p>
            </div>
            <div className="flex items-center gap-3">
              <WorkflowTrigger
                workflowName="upload"
                customWorkflowInput={(files, fieldValues) => {
                  return {
                    file_id: files[0].fileId,
                    index_name: INDEX_NAME,
                  };
                }}
              />
              {anyActiveHandlers && (
                <Loader className="w-4 h-4 animate-spin text-muted-foreground" />
              )}
            </div>
          </header>

          {/* Main chat area */}
          <div className="flex-1 overflow-hidden">
            {!chatHistory.loading && (
              <ChatBot
                key={`${chatHistory.chatCounter}-${chatHistory.selectedChatId || "new"}`}
                handlerId={chatHistory.selectedChatId ?? undefined}
                onHandlerCreated={(handler) => {
                  chatHistory.addChat(handler);
                  chatHistory.setSelectedChatId(handler);
                }}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
