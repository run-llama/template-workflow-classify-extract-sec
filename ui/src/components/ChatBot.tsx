// This is a temporary chatbot component that is used to test the chatbot functionality.
// LlamaIndex will replace it with better chatbot component.
import { useChatbot } from "@/libs/useChatbot";
import { Button, cn, ScrollArea, Textarea } from "@llamaindex/ui";
import { Bot, Loader2, RefreshCw, Send, User } from "lucide-react";
import { FormEvent, KeyboardEvent, useEffect, useRef } from "react";

export default function ChatBot({
  handlerId,
  onHandlerCreated,
}: {
  handlerId?: string;
  onHandlerCreated?: (handlerId: string) => void;
}) {
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatbot = useChatbot({
    handlerId,
    onHandlerCreated,
    focusInput: () => {
      inputRef.current?.focus();
    },
  });

  // UI text defaults
  const title = "AI Document Assistant";
  const placeholder = "Ask me anything about your documents...";

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatbot.messages]);

  // Reset textarea height when input is cleared
  useEffect(() => {
    if (!chatbot.input && inputRef.current) {
      inputRef.current.style.height = "48px"; // Reset to initial height
    }
  }, [chatbot.input]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    await chatbot.submit();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Submit on Enter (without Shift)
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as any);
    }
    // Allow Shift+Enter to create new line (default behavior)
  };

  const adjustTextareaHeight = (textarea: HTMLTextAreaElement) => {
    textarea.style.height = "auto";
    textarea.style.height = Math.min(textarea.scrollHeight, 128) + "px"; // 128px = max-h-32
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    chatbot.setInput(e.target.value);
    adjustTextareaHeight(e.target);
  };

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Simplified header - only show retry button when needed */}
      {chatbot.messages.some((m) => m.error) && (
        <div className="flex justify-center">
          <div className="w-full max-w-4xl px-4 py-2 border-b bg-muted/30">
            <button
              onClick={chatbot.retryLastMessage}
              className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
              title="Retry last message"
            >
              <RefreshCw className="w-4 h-4" />
              Retry last message
            </button>
          </div>
        </div>
      )}

      {/* Messages */}
      <ScrollArea className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto p-6">
          {chatbot.messages.length === 0 ? (
            <div className="flex items-center justify-center h-full min-h-[400px]">
              <div className="text-center">
                <Bot className="w-16 h-16 text-muted-foreground/50 mx-auto mb-4" />
                <p className="text-lg text-foreground mb-2">
                  Welcome! 👋 Upload a document with the control above, then ask
                  questions here.
                </p>
                <p className="text-sm text-muted-foreground">
                  Start by uploading a document to begin your conversation
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {chatbot.messages.map((message, i) => (
                <div
                  key={i}
                  className={cn(
                    "flex gap-4",
                    message.role === "user" ? "justify-end" : "justify-start",
                  )}
                >
                  {message.role !== "user" && (
                    <div
                      className={cn(
                        "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-1",
                        message.error
                          ? "bg-destructive/10 text-destructive"
                          : "bg-primary/10 text-primary",
                      )}
                    >
                      <Bot className="w-5 h-5" />
                    </div>
                  )}
                  <div
                    className={cn(
                      "max-w-[75%]",
                      message.role === "user" ? "order-1" : "order-2",
                    )}
                  >
                    <div
                      className={cn(
                        "rounded-2xl px-4 py-3",
                        message.role === "user"
                          ? "bg-primary text-primary-foreground"
                          : message.error
                            ? "bg-destructive/5 border border-destructive/20"
                            : "bg-muted",
                      )}
                    >
                      {message.isPartial && !message.content ? (
                        <div className="m-2">
                          <LoadingDots />
                        </div>
                      ) : (
                        <p className="whitespace-pre-wrap text-sm leading-relaxed">
                          {message.content}
                        </p>
                      )}
                      <p
                        className={cn(
                          "text-xs mt-2 opacity-60",
                          message.role === "user"
                            ? "text-primary-foreground"
                            : message.error
                              ? "text-destructive"
                              : "text-muted-foreground",
                        )}
                      >
                        {message.timestamp.toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                  {message.role === "user" && (
                    <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center flex-shrink-0 order-2 mt-1">
                      <User className="w-5 h-5 text-muted-foreground" />
                    </div>
                  )}
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Input */}
      <div className="border-t bg-background">
        <div className="max-w-4xl mx-auto p-6">
          <form onSubmit={handleSubmit} className="flex gap-3">
            <Textarea
              ref={inputRef}
              value={chatbot.input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              disabled={chatbot.isLoading}
              className="flex-1 min-h-12 max-h-32 rounded-xl border-2 focus:border-primary resize-none overflow-hidden"
              autoFocus
              style={{ height: "48px" }} // Initial height (min-h-12)
            />
            <Button
              type="submit"
              disabled={
                !chatbot.canSend || chatbot.isLoading || !chatbot.input.trim()
              }
              size="icon"
              title="Send message"
              className="h-12 w-12 rounded-xl"
            >
              {!chatbot.canSend || chatbot.isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </Button>
          </form>
          <p className="text-xs text-muted-foreground mt-3 text-center">
            Press Enter to send • Shift+Enter for new line
          </p>
        </div>
      </div>
    </div>
  );
}

const LoadingDots = () => {
  return (
    <div className="flex items-center gap-2">
      <div className="flex gap-1">
        <span
          className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"
          style={{ animationDelay: "0ms" }}
        ></span>
        <span
          className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"
          style={{ animationDelay: "150ms" }}
        ></span>
        <span
          className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"
          style={{ animationDelay: "300ms" }}
        ></span>
      </div>
    </div>
  );
};
