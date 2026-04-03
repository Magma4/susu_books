"use client";
/**
 * ChatBubble — Displays the last AI response in a conversational bubble.
 * Includes a subtle typing animation when new content arrives.
 */

import { useEffect, useRef, useState } from "react";
import type { ChatMessage } from "@/lib/types";

interface ChatBubbleProps {
  messages: ChatMessage[];
  isTyping?: boolean;
}

export default function ChatBubble({ messages, isTyping }: ChatBubbleProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, isTyping]);

  if (!messages.length && !isTyping) return null;

  return (
    <div className="bg-white rounded-2xl border border-border shadow-card overflow-hidden">
      {/* Header */}
      <div className="px-4 py-2.5 border-b border-border flex items-center gap-2">
        {/* Susu avatar */}
        <div className="h-6 w-6 rounded-full bg-primary-900 flex items-center justify-center flex-shrink-0">
          <span className="text-white text-[10px] font-bold">S</span>
        </div>
        <span className="text-xs font-semibold text-text-secondary uppercase tracking-wide">
          Susu Books
        </span>
      </div>

      {/* Message thread */}
      <div className="px-4 py-3 space-y-3 max-h-48 overflow-y-auto">
        {messages.map((msg) => (
          <MessageRow key={msg.id} message={msg} />
        ))}

        {/* Typing indicator */}
        {isTyping && (
          <div className="flex items-center gap-1.5 py-1">
            <TypingDot delay="0ms" />
            <TypingDot delay="160ms" />
            <TypingDot delay="320ms" />
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function MessageRow({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div
      className={`flex gap-2 animate-fade-in ${isUser ? "flex-row-reverse" : "flex-row"}`}
    >
      {/* Role badge */}
      <div
        className={`
          h-5 w-5 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5
          ${isUser ? "bg-accent-light" : "bg-primary-surface"}
        `}
      >
        <span
          className={`text-[9px] font-bold ${
            isUser ? "text-accent-900" : "text-primary-900"
          }`}
        >
          {isUser ? "U" : "S"}
        </span>
      </div>

      {/* Bubble */}
      <div
        className={`
          rounded-2xl px-3 py-2 text-sm leading-relaxed max-w-[85%]
          ${
            isUser
              ? "bg-accent-light text-text-primary rounded-tr-sm"
              : "bg-primary-surface text-primary-900 rounded-tl-sm"
          }
        `}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        <p className="text-2xs mt-1 opacity-50">
          {message.timestamp.toLocaleTimeString("en-GH", {
            hour: "numeric",
            minute: "2-digit",
          })}
        </p>
      </div>
    </div>
  );
}

function TypingDot({ delay }: { delay: string }) {
  return (
    <span
      className="h-2 w-2 rounded-full bg-primary-light animate-bounce-dot"
      style={{ animationDelay: delay }}
    />
  );
}
