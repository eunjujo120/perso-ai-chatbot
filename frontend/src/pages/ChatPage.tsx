// src/pages/ChatPage.tsx
import React, { useState, useRef, useEffect } from "react";
import { sendChatMessage, type ChatResponse } from "../lib/api";

type Role = "user" | "assistant" | "system";

interface Message {
  id: string;
  role: Role;
  content: string;
}

const initialSystemMessage: Message = {
  id: "system-1",
  role: "system",
  content: "안녕하세요! 👋 Perso AI 상담 챗봇입니다.",
};

function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([initialSystemMessage]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: trimmed,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const res: ChatResponse = await sendChatMessage(trimmed);

      const botMsg: Message = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: res.answer,
      };

      setMessages((prev) => [...prev, botMsg]);
    } catch (err: any) {
      const errorMsg: Message = {
        id: `error-${Date.now()}`,
        role: "assistant",
        content:
          "서버와 통신 중 오류가 발생했어요. 잠시 후 다시 시도해 주세요.\n\n" +
          (err?.message || ""),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full max-w-5xl h-[min(720px,calc(100vh-120px))] bg-white border border-zinc-200 shadow-2xl rounded-3xl flex flex-col overflow-hidden">
      {/* 카드 상단: 설명 영역 */}
      <div className="border-b border-zinc-100 px-6 py-4 bg-gradient-to-r from-[#f4f3ff] via-white to-[#f4f3ff]">
        <h2 className="text-lg font-semibold text-zinc-900">Perso AI 챗봇</h2>
        <p className="text-xs text-zinc-500 mt-1">
          Perso.ai 관련 Q&A 데이터만을 기반으로, 존재하는 답변만 정직하게 알려드려요.
        </p>
      </div>

      {/* 메시지 영역 */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-4 space-y-3.5 bg-white">
        {messages.map((m) => (
          <ChatBubble key={m.id} message={m} />
        ))}

        {isLoading && (
          <div className="flex items-start gap-2">
            <div className="h-8 w-8 rounded-full bg-[#7b5cff] flex items-center justify-center text-xs font-bold text-white flex-shrink-0 mt-1">
              P
            </div>
            <div className="bg-zinc-100 px-3 py-2 rounded-2xl rounded-tl-sm text-sm text-zinc-700">
              <span className="inline-flex gap-1">
                <span className="animate-pulse">●</span>
                <span className="animate-pulse [animation-delay:150ms]">
                  ●
                </span>
                <span className="animate-pulse [animation-delay:300ms]">
                  ●
                </span>
              </span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* 입력 영역 */}
      <form
        onSubmit={handleSubmit}
        className="border-t border-zinc-100 px-4 sm:px-6 py-3 bg-white"
      >
        <div className="flex items-end gap-2.5">
          <textarea
            className="flex-1 resize-none rounded-2xl border border-zinc-300 bg-zinc-50 px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-[#7b5cff]/60 focus:border-[#7b5cff] max-h-32"
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="질문을 입력하세요. 예) Perso.ai는 어떤 서비스인가요?"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="inline-flex items-center justify-center rounded-2xl bg-[#7b5cff] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[#6b50f2] transition-colors active:bg-[#5a43dc]"
          >
            보내기
          </button>
        </div>
      </form>
    </div>
  );
}

interface ChatBubbleProps {
  message: Message;
}

function ChatBubble({ message }: ChatBubbleProps) {
  if (message.role === "system") {
    return (
      <div className="flex justify-center">
        <div className="max-w-[90%] text-xs text-zinc-600 bg-zinc-100 px-3 py-1.5 rounded-full">
          {message.content}
        </div>
      </div>
    );
  }

  const isUser = message.role === "user";

  return (
    <div
      className={`flex w-full ${
        isUser ? "justify-end" : "justify-start"
      } gap-2`}
    >
      {/* 봇 아이콘 */}
      {!isUser && (
        <div className="h-8 w-8 rounded-full bg-[#7b5cff] flex items-center justify-center text-xs font-bold text-white flex-shrink-0 mt-1">
          P
        </div>
      )}

      {/* 말풍선 */}
      <div
        className={`max-w-xl break-words text-sm px-3 py-2 rounded-2xl ${
          isUser
            ? "bg-[#7b5cff] text-white rounded-br-sm"
            : "bg-white text-zinc-900 border border-zinc-200 shadow-sm rounded-tl-sm"
        }`}
      >
        {message.content}
      </div>

      {isUser && <div className="w-8 flex-shrink-0" />}
    </div>
  );
}

export default ChatPage;
