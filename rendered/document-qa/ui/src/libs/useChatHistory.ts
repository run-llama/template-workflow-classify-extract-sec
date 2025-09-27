import { IDBPDatabase, openDB } from "idb";
import { useEffect, useState } from "react";

export interface ChatHistory {
  handlerId: string;
  timestamp: string;
}

export interface UseChatHistory {
  loading: boolean;
  addChat(handlerId: string): void;
  deleteChat(handlerId: string): void;
  chats: ChatHistory[];
  selectedChatId: string | null;
  setSelectedChatId(handlerId: string): void;
  createNewChat(): void;
  // forces a new chat
  chatCounter: number;
}

const DB_NAME = "chat-history";
const DB_VERSION = 1;
const STORE_NAME = "chats";

/**
 * Hook that tracks workflow handler ids, to use as markers of a chat conversation that can be reloaded.
 * Stores chats in IndexedDB
 * @returns
 */
export function useChatHistory(): UseChatHistory {
  const [loading, setLoading] = useState(true);
  const [chatHistory, setChatHistory] = useState<ChatHistory[]>([]);
  const [selectedChatHandlerId, setSelectedChatHandlerId] = useState<
    string | null
  >(null);
  const [db, setDb] = useState<IDBPDatabase<unknown> | null>(null);
  const [chatCounter, setChatCounter] = useState(0);

  // Initialize database
  useEffect(() => {
    let thisDb: IDBPDatabase<unknown> | null = null;

    const initDb = async () => {
      try {
        thisDb = await openDB(DB_NAME, DB_VERSION, {
          upgrade(db) {
            if (!db.objectStoreNames.contains(STORE_NAME)) {
              const store = db.createObjectStore(STORE_NAME, {
                keyPath: "handlerId",
              });
              store.createIndex("timestamp", "timestamp");
            }
          },
        });
        setDb(thisDb);
      } catch (error) {
        console.error("Failed to initialize database:", error);
        setLoading(false);
      }
    };

    initDb();

    return () => {
      thisDb?.close();
    };
  }, []);

  // Load chat history when database is ready
  useEffect(() => {
    if (!db) return;

    const loadChats = async () => {
      try {
        setLoading(true);
        const chats = await getChatsFromDb();
        setChatHistory(chats);

        // Initialize selectedChat to the latest chat (first in sorted array)
        if (chats.length > 0 && !selectedChatHandlerId) {
          setSelectedChatHandlerId(chats[0].handlerId);
        }
      } catch (error) {
        console.error("Failed to load chat history:", error);
      } finally {
        setLoading(false);
      }
    };

    loadChats();
  }, [db]);

  const getChatsFromDb = async (): Promise<ChatHistory[]> => {
    if (!db) return [];

    try {
      const transaction = db.transaction(STORE_NAME, "readonly");
      const store = transaction.objectStore(STORE_NAME);
      const index = store.index("timestamp");
      const chats = await index.getAll();

      // Sort by timestamp descending (most recent first)
      return chats.sort(
        (a, b) =>
          new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
      );
    } catch (error) {
      console.error("Failed to get chats from database:", error);
      return [];
    }
  };

  const addChat = async (handlerId: string): Promise<void> => {
    if (!db) return;

    try {
      const chat: ChatHistory = {
        handlerId,
        timestamp: new Date().toISOString(),
      };

      const transaction = db.transaction(STORE_NAME, "readwrite");
      const store = transaction.objectStore(STORE_NAME);
      await store.put(chat);

      // Update local state
      setChatHistory((prev) => [
        chat,
        ...prev.filter((c) => c.handlerId !== handlerId),
      ]);

      // Set as selected chat if it's the first chat or if no chat is currently selected
      if (!selectedChatHandlerId) {
        setSelectedChatHandlerId(chat.handlerId);
      }
    } catch (error) {
      console.error("Failed to add chat to database:", error);
    }
  };

  const deleteChat = async (handlerId: string): Promise<void> => {
    if (!db) return;

    try {
      const transaction = db.transaction(STORE_NAME, "readwrite");
      const store = transaction.objectStore(STORE_NAME);
      await store.delete(handlerId);

      // Update local state
      setChatHistory((prev) => prev.filter((c) => c.handlerId !== handlerId));

      // If the deleted chat was selected, select the next available chat or clear selection
      if (selectedChatHandlerId === handlerId) {
        const remainingChats = chatHistory.filter(
          (c) => c.handlerId !== handlerId,
        );
        if (remainingChats.length > 0) {
          setSelectedChatHandlerId(remainingChats[0].handlerId);
          setChatCounter((prev) => prev + 1);
        } else {
          setSelectedChatHandlerId(null);
          setChatCounter((prev) => prev + 1);
        }
      }
    } catch (error) {
      console.error("Failed to delete chat from database:", error);
    }
  };

  const createNewChat = (): void => {
    setSelectedChatHandlerId(null);
    setChatCounter((prev) => prev + 1);
  };

  return {
    loading,
    addChat,
    chats: chatHistory,
    selectedChatId: selectedChatHandlerId,
    setSelectedChatId: setSelectedChatHandlerId,
    deleteChat,
    createNewChat,
    chatCounter,
  };
}
