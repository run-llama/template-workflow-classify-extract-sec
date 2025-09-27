// This is a temporary chatbot component that is used to test the chatbot functionality.
// LlamaIndex will replace it with better chatbot component.
import { WorkflowEvent } from "@llamaindex/ui";
import { useEffect, useRef, useState } from "react";
import { useChatWorkflowHandler } from "./useChatWorkflowHandler";
import { createHumanResponseEvent } from "./events";

export type Role = "user" | "assistant";
export interface Message {
  role: Role;
  isPartial?: boolean;
  content: string;
  timestamp: Date;
  error?: boolean;
}

export interface ChatbotState {
  submit(): Promise<void>;
  retryLastMessage: () => void;
  setInput: (input: string) => void;

  messages: Message[];
  input: string;
  isLoading: boolean;
  canSend: boolean;
}

export function useChatbot({
  handlerId,
  onHandlerCreated,
  focusInput: focusInput,
}: {
  handlerId?: string;
  onHandlerCreated?: (handlerId: string) => void;
  focusInput?: () => void;
}): ChatbotState {
  const workflowHandler = useChatWorkflowHandler({
    handlerId,
    onHandlerCreated,
  });
  const { events } = workflowHandler;
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const lastProcessedEventIndexRef = useRef<number>(0);
  const [canSend, setCanSend] = useState<boolean>(false);

  // Whenever handler becomes defined and changed, stop loading
  useEffect(() => {
    if (handlerId) {
      setIsLoading(false);
      setCanSend(true);
    }
  }, [handlerId]);

  const welcomeMessage =
    "Welcome! 👋 Upload a document with the control above, then ask questions here.";

  // Initialize with welcome message
  useEffect(() => {
    if (messages.length === 0) {
      const welcomeMsg: Message = {
        role: "assistant",
        content: welcomeMessage,
        timestamp: new Date(),
      };
      setMessages([welcomeMsg]);
    }
  }, []);

  // Process streamed events into messages
  useEffect(() => {
    if (!events || events.length === 0) return;
    let startIdx = lastProcessedEventIndexRef.current;
    if (startIdx < 0) startIdx = 0;
    if (startIdx >= events.length) return;

    const eventsToProcess = events.slice(startIdx);
    const newMessages = toMessages(eventsToProcess);
    if (newMessages.length > 0) {
      setMessages((prev) => mergeMessages(prev, newMessages));
    }
    for (const ev of eventsToProcess) {
      const type = ev.type;
      if (!type) continue;
      if (type.endsWith(".InputRequiredEvent")) {
        // ready for next user input; enable send
        setCanSend(true);
        setIsLoading(false);
      } else if (type.endsWith(".StopEvent")) {
        // finished; no summary bubble needed (chat response already streamed)
      }
    }
    lastProcessedEventIndexRef.current = events.length;
  }, [events, messages]);

  const retryLastMessage = () => {
    const lastUserMessage = messages.filter((m) => m.role === "user").pop();
    if (lastUserMessage) {
      // Remove the last assistant message if it was an error
      const lastMessage = messages[messages.length - 1];
      if (lastMessage.role === "assistant" && lastMessage.error) {
        setMessages((prev) => prev.slice(0, -1));
      }
      setInput(lastUserMessage.content);
      focusInput?.();
    }
  };

  const submit = async () => {
    const trimmedInput = input.trim();
    if (!trimmedInput || isLoading || !canSend) return;

    // Add user message
    const userMessage: Message = {
      role: "user",
      content: trimmedInput,
      timestamp: new Date(),
    };
    const placeHolderMessage: Message = {
      role: "assistant",
      content: "",
      timestamp: new Date(),
      isPartial: true,
    };

    const newMessages = [...messages, userMessage, placeHolderMessage];
    setMessages(newMessages);
    setInput("");
    setIsLoading(true);
    setCanSend(false);

    try {
      // Send user input as HumanResponseEvent
      await workflowHandler.sendEvent(createHumanResponseEvent(trimmedInput));
    } catch (err) {
      console.error("Chat error:", err);

      // Add error message
      const errorMessage: Message = {
        role: "assistant",
        content: `Sorry, I encountered an error: ${err instanceof Error ? err.message : "Unknown error"}. Please try again.`,
        timestamp: new Date(),
        error: true,
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      // Focus back on input
      focusInput?.();
    }
  };

  return {
    submit,
    retryLastMessage,
    messages,
    input,
    setInput,
    isLoading,
    canSend,
  };
}

interface AppendChatMessageData {
  message: ChatMessage;
}
interface ErrorEventData {
  error: string;
}
interface ChatMessage {
  role: "user" | "assistant";
  text: string;
  sources: {
    text: string;
    score: number;
    metadata: Record<string, any>;
  }[];
  timestamp: string;
}

function mergeMessages(previous: Message[], current: Message[]): Message[] {
  const lastPreviousMessage = previous[previous.length - 1];
  const restPrevious = previous.slice(0, -1);
  const firstCurrentMessage = current[0];
  const restCurrent = current.slice(1);
  if (!lastPreviousMessage || !firstCurrentMessage) {
    return [...previous, ...current];
  }
  if (lastPreviousMessage.isPartial && firstCurrentMessage.isPartial) {
    const lastContent =
      lastPreviousMessage.content === "Thinking..."
        ? ""
        : lastPreviousMessage.content;
    const merged = {
      ...lastPreviousMessage,
      content: lastContent + firstCurrentMessage.content,
    };
    return [...restPrevious, merged, ...restCurrent];
  } else if (
    lastPreviousMessage.isPartial &&
    firstCurrentMessage.role === lastPreviousMessage.role
  ) {
    return [...restPrevious, firstCurrentMessage, ...restCurrent];
  } else {
    return [...previous, ...current];
  }
}

function toMessages(events: WorkflowEvent[]): Message[] {
  const messages: Message[] = [];
  for (const ev of events) {
    const type = ev.type;
    const data = ev.data as any;
    const lastMessage = messages[messages.length - 1];
    if (type.endsWith(".ChatDeltaEvent")) {
      const delta: string = data?.delta ?? "";
      if (!delta) continue;
      if (!lastMessage || !lastMessage.isPartial) {
        messages.push({
          role: "assistant",
          content: delta,
          isPartial: true,
          timestamp: new Date(),
        });
      } else {
        lastMessage.content += delta;
      }
    } else if (type.endsWith(".AppendChatMessage")) {
      if (
        lastMessage &&
        lastMessage.isPartial &&
        lastMessage.role === "assistant"
      ) {
        messages.pop();
      }
      const content = ev.data as unknown as AppendChatMessageData;
      messages.push({
        role: content.message.role,
        content: content.message.text,
        timestamp: new Date(content.message.timestamp),
        isPartial: false,
      });
    } else if (type.endsWith(".ErrorEvent")) {
      if (
        lastMessage &&
        lastMessage.isPartial &&
        lastMessage.role === "assistant"
      ) {
        messages.pop();
      }
      const content = ev.data as unknown as ErrorEventData;
      messages.push({
        role: "assistant",
        content: content.error,
        timestamp: new Date(),
        isPartial: false,
        error: true,
      });
    }
  }
  return messages;
}
