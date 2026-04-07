"use client";

import * as React from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import {
  Clock3,
  LoaderIcon,
  MessageSquarePlus,
  PanelLeftClose,
  PanelLeftOpen,
  SendIcon,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  status?: string;
}

interface SessionSummary {
  id: string;
  title: string;
  last_message_at?: string;
}

interface ServerMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  metadata?: Record<string, unknown>;
  created_at?: string;
}

function useAutoResizeTextarea(minHeight: number) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const resize = useCallback((reset = false) => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    textarea.style.height = `${minHeight}px`;
    textarea.style.overflowY = "hidden";
    if (reset) return;

    textarea.style.height = `${Math.max(textarea.scrollHeight, minHeight)}px`;
  }, [minHeight]);

  useEffect(() => {
    resize();
  }, [resize]);

  return { textareaRef, resize };
}

function MessageRow({
  role,
  content,
  status,
}: {
  role: "user" | "assistant";
  content: string;
  status?: string;
}) {
  const isUser = role === "user";
  return (
    <div className={cn("flex w-full", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[min(780px,90%)] text-[15px] leading-7",
          isUser
            ? "rounded-2xl px-4 py-3 shadow-sm bg-[#2563eb] text-white"
            : "py-3 text-white/90"
        )}
      >
        {isUser ? (
          <div className="whitespace-pre-wrap">{content}</div>
        ) : (
          <div className="flex flex-col gap-2">
            {!content && status && (
              <div className="flex items-center gap-2 text-[13px] text-white/50 animate-pulse">
                <LoaderIcon className="h-3.5 w-3.5 animate-spin" />
                {status}
              </div>
            )}
            {content && (
              <div className="prose prose-invert prose-p:leading-relaxed prose-pre:p-0 max-w-none break-words">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {content}
                </ReactMarkdown>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export function AnimatedAIChat() {
  const apiBaseUrl =
    process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || "http://127.0.0.1:8000";

  const [value, setValue] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [isExplicitNewChat, setIsExplicitNewChat] = useState(false);

  const { textareaRef, resize } = useAutoResizeTextarea(56);

  const scrollRef = useRef<HTMLDivElement>(null);

  const fetchJson = useCallback(
    async <T,>(path: string, init?: RequestInit): Promise<T> => {
      const response = await fetch(`${apiBaseUrl}${path}`, init);
      if (!response.ok) {
        const errorBody = await response.json().catch(() => null);
        throw new Error(errorBody?.detail || `Request failed (${response.status})`);
      }
      return (await response.json()) as T;
    },
    [apiBaseUrl]
  );

  const loadSessions = useCallback(async () => {
    setLoadingSessions(true);
    try {
      const data = await fetchJson<SessionSummary[]>("/sessions");
      setSessions(data);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "Failed to load sessions");
    } finally {
      setLoadingSessions(false);
    }
  }, [fetchJson]);

  const openSession = useCallback(
    async (sessionId: string, sessionsOverride?: SessionSummary[]) => {
      setCurrentSessionId(sessionId);
      setLoadingMessages(true);
      setApiError(null);
      try {
        const data = await fetchJson<ServerMessage[]>(`/sessions/${sessionId}/messages`);
        const normalized = data
          .filter((item) => item.role === "user" || item.role === "assistant")
          .map((item) => ({
            role: item.role as "user" | "assistant",
            content: item.content,
          }));
        setMessages(normalized);
        if (sessionsOverride) {
          setSessions(sessionsOverride);
        }
      } catch (error) {
        setApiError(error instanceof Error ? error.message : "Failed to load messages");
      } finally {
        setLoadingMessages(false);
      }
    },
    [fetchJson]
  );

  const createNewChat = useCallback(() => {
    setCurrentSessionId(null);
    setMessages([]);
    setValue("");
    resize(true);
    setApiError(null);
    setIsExplicitNewChat(true);
  }, [resize]);

  useEffect(() => {
    void loadSessions();
  }, [loadSessions]);

  useEffect(() => {
    if (!isExplicitNewChat && !currentSessionId && !loadingSessions && sessions.length > 0 && messages.length === 0) {
      void openSession(sessions[0].id);
    }
  }, [isExplicitNewChat, currentSessionId, loadingSessions, sessions, messages.length, openSession]);

  useEffect(() => {
    const current = scrollRef.current;
    if (current) {
      current.scrollTop = current.scrollHeight;
    }
  }, [messages, loadingMessages, sending]);

  const handleSend = useCallback(async () => {
    const question = value.trim();
    if (!question || sending) return;

    setSending(true);
    setApiError(null);
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setValue("");
    resize(true);

    try {
      setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

      const response = await fetch(`${apiBaseUrl}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, session_id: currentSessionId }),
      });

      if (!response.ok) {
        throw new Error(`Request failed (${response.status})`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) throw new Error("No reader");

      let done = false;
      let streamedResponse = "";
      let buffer = "";

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          buffer += chunk;

          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.slice(6);
              if (dataStr === '[DONE]') {
                done = true;
                break;
              }
              try {
                const data = JSON.parse(dataStr);
                if (data.type === 'session_init') {
                  if (data.session_id && data.session_id !== currentSessionId) {
                    setCurrentSessionId(data.session_id);
                  }
                } else if (data.type === 'status') {
                  setMessages((prev) => {
                    const newMessages = [...prev];
                    newMessages[newMessages.length - 1].status = data.content;
                    return newMessages;
                  });
                } else if (data.type === 'content') {
                  streamedResponse += data.content;
                  setMessages((prev) => {
                    const newMessages = [...prev];
                    newMessages[newMessages.length - 1].content = streamedResponse;
                    return newMessages;
                  });
                } else if (data.type === 'error') {
                  setApiError(data.content);
                }
              } catch (e) {
                console.error("Error parsing stream chunk", e);
              }
            }
          }
        }
      }

      if (!streamedResponse) {
        setMessages((prev) => {
          const newMessages = [...prev];
          newMessages[newMessages.length - 1].content = "No answer returned.";
          return newMessages;
        });
      }
      await loadSessions();
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "Unexpected API error");
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "I could not reach the backend. Make sure FastAPI is running and GROQ_API_KEY is configured.",
        },
      ]);
    } finally {
      setSending(false);
    }
  }, [value, sending, fetchJson, currentSessionId, loadSessions, resize]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  return (
    <div className="flex h-[100dvh] w-full overflow-hidden bg-[#0b0b0c] text-white">
      <aside
        className={cn(
          "hidden shrink-0 border-r border-white/10 bg-[#111113] transition-all duration-200 md:flex",
          sidebarOpen ? "w-80" : "w-16"
        )}
      >
        <div className="flex h-screen w-full flex-col p-3">
          <div className="flex items-center justify-between gap-2 px-2 py-2">
            {sidebarOpen ? (
              <div className="text-sm font-medium text-white/80">Conversations</div>
            ) : (
              <div className="text-xs text-white/50">Chat</div>
            )}
            <button
              type="button"
              onClick={() => setSidebarOpen((prev) => !prev)}
              className="rounded-md p-2 text-white/60 hover:bg-white/10 hover:text-white"
              aria-label="Toggle sidebar"
            >
              {sidebarOpen ? <PanelLeftClose className="h-4 w-4" /> : <PanelLeftOpen className="h-4 w-4" />}
            </button>
          </div>

          <button
            type="button"
            onClick={createNewChat}
            className={cn(
              "mt-3 flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-3 text-sm text-white/90 hover:bg-white/10",
              !sidebarOpen && "justify-center px-2"
            )}
          >
            <MessageSquarePlus className="h-4 w-4 shrink-0" />
            {sidebarOpen && <span>New chat</span>}
          </button>

          <div className="mt-4 flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto pr-1">
            {loadingSessions && <div className="px-2 text-xs text-white/50">Loading...</div>}
            {sessions.map((session) => (
              <button
                key={session.id}
                type="button"
                onClick={() => void openSession(session.id)}
                className={cn(
                  "rounded-xl px-3 py-3 text-left transition-colors",
                  currentSessionId === session.id
                    ? "bg-white/12 text-white"
                    : "bg-white/0 text-white/70 hover:bg-white/5"
                )}
              >
                <div className="truncate text-sm font-medium">
                  {sidebarOpen ? session.title : session.title.slice(0, 1)}
                </div>
                {sidebarOpen && (
                  <div className="mt-1 flex items-center gap-1 text-[11px] text-white/40">
                    <Clock3 className="h-3 w-3" />
                    <span className="truncate">
                      {session.last_message_at
                        ? new Date(session.last_message_at).toLocaleString()
                        : "No activity"}
                    </span>
                  </div>
                )}
              </button>
            ))}
          </div>
        </div>
      </aside>

      <main className="flex min-w-0 flex-1 flex-col overflow-hidden bg-[#0b0b0c]">
        <div className="flex h-14 shrink-0 items-center justify-between border-b border-white/10 px-4 sm:px-6">
          <div>
            <div className="text-sm font-medium text-white/70">Adaptive RAG</div>
            <div className="text-xs text-white/40">Chat with your documents</div>
          </div>
          <div className="text-xs text-white/35">{currentSessionId ? "Conversation open" : "New chat"}</div>
        </div>

        <div className="flex min-h-0 flex-1 flex-col px-3 py-3 sm:px-6 sm:py-6">
          <section className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-3xl border border-white/10 bg-white/[0.02]">
            <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto px-3 py-4 sm:px-6 sm:py-6">
              {loadingMessages && (
                <div className="rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white/60">
                  Loading conversation...
                </div>
              )}

              {!loadingMessages && messages.length === 0 && (
                <div className="flex min-h-[40vh] flex-col items-center justify-center text-center">
                  <h1 className="text-3xl font-medium tracking-tight text-white/90 sm:text-4xl">
                    How can I help today?
                  </h1>
                  <p className="mt-3 max-w-lg text-sm leading-6 text-white/45">
                    Ask a question or open an existing conversation from the sidebar.
                  </p>
                </div>
              )}

              <div className="space-y-4">
                {messages.map((message, index) => (
                  <MessageRow key={`${message.role}-${index}`} role={message.role} content={message.content} status={message.status} />
                ))}
              </div>
            </div>

            <div className="shrink-0 border-t border-white/10 bg-[#0b0b0c] px-3 py-3 sm:px-6 sm:py-4">
              <div className="rounded-3xl border border-white/10 bg-[#151518] p-3 shadow-[0_20px_60px_rgba(0,0,0,0.35)]">
                <div className="flex items-end gap-3">
                  <textarea
                    ref={textareaRef}
                    value={value}
                    onChange={(e) => {
                      setValue(e.target.value);
                      resize();
                    }}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask anything"
                    rows={1}
                    className={cn(
                      "min-h-[56px] flex-1 resize-none overflow-hidden bg-transparent px-1 py-3 text-[15px] leading-6 text-white outline-none placeholder:text-white/30"
                    )}
                  />

                  <button
                    type="button"
                    onClick={() => void handleSend()}
                    disabled={sending || !value.trim()}
                    className={cn(
                      "mb-1 inline-flex h-11 w-11 items-center justify-center rounded-full transition-colors",
                      value.trim() ? "bg-white text-black hover:opacity-90" : "bg-white/10 text-white/40"
                    )}
                    aria-label="Send message"
                  >
                    {sending ? <LoaderIcon className="h-4 w-4 animate-spin" /> : <SendIcon className="h-4 w-4" />}
                  </button>
                </div>

                <div className="mt-2 flex items-center justify-between gap-3 px-1 text-xs text-white/35">
                  <span>Press Enter to send, Shift+Enter for a new line.</span>
                  {apiError && <span className="text-red-300">{apiError}</span>}
                </div>
              </div>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
