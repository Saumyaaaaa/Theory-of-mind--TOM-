"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Send,
  RotateCcw,
  Bot,
  User,
  ShieldCheck,
  Sparkles,
  BookOpen,
  AlertCircle,
  SlidersHorizontal,
} from "lucide-react";
import DebugPanel, { SnapshotItem } from "@/components/DebugPanel";

interface Message {
  id?: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at?: string;
}

interface VerificationMeta {
  attempts_count: number;
  used_fallback: boolean;
  mastered_concepts: string[];
  locked_concepts: string[];
}

const BACKEND_URL = "http://127.0.0.1:8000";
const STORAGE_KEY = "learner_tutor_session_id";

export default function ChatPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [probedConcept, setProbedConcept] = useState<string | null>(null);
  const [verificationMeta, setVerificationMeta] = useState<VerificationMeta | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isDebugOpen, setIsDebugOpen] = useState(false);
  const [conceptGraph, setConceptGraph] = useState<Record<string, { prereqs: string[] }>>({});
  const [activeSnapshot, setActiveSnapshot] = useState<SnapshotItem | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll chat to latest message
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Load concept graph ontology
  useEffect(() => {
    const fetchOntology = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/concept-graph`);
        if (res.ok) {
          const data = await res.json();
          setConceptGraph(data);
        }
      } catch (e) {
        console.warn("Failed to load concept ontology", e);
      }
    };
    fetchOntology();
  }, []);

  // Session initialization / resumption logic
  useEffect(() => {
    const initOrResumeSession = async () => {
      setErrorMsg(null);
      const savedSessionId = typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null;

      if (savedSessionId) {
        try {
          const [msgRes, stateRes] = await Promise.all([
            fetch(`${BACKEND_URL}/messages/${savedSessionId}`),
            fetch(`${BACKEND_URL}/state/${savedSessionId}`),
          ]);

          if (msgRes.ok && stateRes.ok) {
            const msgData = await msgRes.json();
            const stateData = await stateRes.json();

            setSessionId(savedSessionId);
            setMessages(msgData.messages || []);
            if (stateData) {
              setActiveSnapshot(stateData);
              if (stateData?.state?.concept_being_probed) {
                setProbedConcept(stateData.state.concept_being_probed);
              }
            }
            return;
          }
        } catch (e) {
          console.warn("Could not resume saved session, creating new session...", e);
        }
      }

      startNewSession();
    };

    initOrResumeSession();
  }, []);

  const startNewSession = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await fetch(`${BACKEND_URL}/session`, { method: "POST" });
      if (!res.ok) {
        throw new Error(`Server returned HTTP ${res.status}`);
      }
      const data = await res.json();
      const newSid = data.session_id;

      if (typeof window !== "undefined") {
        localStorage.setItem(STORAGE_KEY, newSid);
      }

      setSessionId(newSid);
      setMessages([
        {
          role: "assistant",
          content: data.reply || "Hello! I'm your algebra tutor. What would you like to explore today?",
        },
      ]);
      setProbedConcept(data.state?.concept_being_probed || "variable");
      setActiveSnapshot({
        id: "initial",
        session_id: newSid,
        message_id: "seed",
        state: data.state,
        mastery: data.mastery,
        created_at: new Date().toISOString(),
      });
      setVerificationMeta(null);
    } catch (err: any) {
      setErrorMsg(`Failed to connect to backend at ${BACKEND_URL}. Ensure uvicorn is running.`);
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmed = inputMessage.trim();
    if (!trimmed || !sessionId || isLoading) return;

    // Optimistically append user message to chat UI
    const userMsg: Message = { role: "user", content: trimmed };
    setMessages((prev) => [...prev, userMsg]);
    setInputMessage("");
    setIsLoading(true);
    setErrorMsg(null);

    try {
      const res = await fetch(`${BACKEND_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          message: trimmed,
        }),
      });

      if (!res.ok) {
        throw new Error(`Chat request failed with HTTP ${res.status}`);
      }

      const data = await res.json();

      // Append assistant's scaffolded reply
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.reply },
      ]);

      if (data.state?.concept_being_probed) {
        setProbedConcept(data.state.concept_being_probed);
      }
      if (data.verification) {
        setVerificationMeta(data.verification);
      }

      setActiveSnapshot({
        id: "turn",
        session_id: sessionId,
        message_id: "latest",
        state: data.state,
        mastery: data.mastery,
        created_at: new Date().toISOString(),
      });
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to get reply from tutor.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Filter out system messages from chat UI
  const visibleMessages = messages.filter((m) => m.role !== "system");

  return (
    <div className="flex h-screen flex-col bg-slate-50 font-sans text-slate-900 overflow-hidden">
      {/* Top Navigation Bar */}
      <header className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-6 shadow-sm z-10">
        <div className="flex items-center space-x-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 text-white shadow-sm">
            <BookOpen className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-base font-semibold text-slate-900">
                Learner-State Scaffolding Tutor
              </h1>
              <span className="inline-flex items-center rounded-md bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700 ring-1 ring-inset ring-indigo-700/10">
                Dual-Agent
              </span>
            </div>
            <p className="text-xs text-slate-500">
              Cognitive Modeler &bull; BKT Tracker &bull; Verifier &bull; Socratic Interlocutor
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {probedConcept && (
            <div className="hidden sm:flex items-center space-x-1.5 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700 border border-slate-200">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>Probing:</span>
              <span className="font-semibold text-slate-900">{probedConcept.replace(/_/g, " ")}</span>
            </div>
          )}

          {verificationMeta && (
            <div className="hidden md:flex items-center space-x-1 rounded-md bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700 border border-emerald-200">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
              <span>Verified ({verificationMeta.attempts_count} att.)</span>
            </div>
          )}

          <button
            onClick={startNewSession}
            disabled={isLoading}
            className="inline-flex items-center space-x-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 transition"
            title="Start a fresh session with reset mastery"
          >
            <RotateCcw className="h-3.5 w-3.5 text-slate-500" />
            <span>Reset</span>
          </button>

          {/* Debug Mode Toggle Button */}
          <button
            onClick={() => setIsDebugOpen((prev) => !prev)}
            className={`inline-flex items-center space-x-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold shadow-sm transition ${
              isDebugOpen
                ? "bg-indigo-600 text-white hover:bg-indigo-700"
                : "bg-slate-900 text-white hover:bg-slate-800"
            }`}
          >
            <SlidersHorizontal className="h-3.5 w-3.5" />
            <span>Debug Mode</span>
          </button>
        </div>
      </header>

      {/* Error Alert Banner */}
      {errorMsg && (
        <div className="bg-red-50 border-b border-red-200 px-6 py-2.5 flex items-center justify-between text-xs text-red-700">
          <div className="flex items-center space-x-2">
            <AlertCircle className="h-4 w-4 shrink-0 text-red-500" />
            <span>{errorMsg}</span>
          </div>
          <button
            onClick={() => setErrorMsg(null)}
            className="text-red-500 hover:text-red-700 font-semibold"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main Chat Feed */}
      <main className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 max-w-4xl w-full mx-auto">
        {visibleMessages.length === 0 ? (
          <div className="flex h-full items-center justify-center text-slate-400 text-sm">
            Initializing tutoring session...
          </div>
        ) : (
          visibleMessages.map((msg, index) => {
            const isUser = msg.role === "user";
            return (
              <div
                key={index}
                className={`flex items-start space-x-3 ${isUser ? "flex-row-reverse space-x-reverse" : "flex-row"}`}
              >
                {/* Avatar Icon */}
                <div
                  className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-medium shadow-sm ${
                    isUser
                      ? "bg-slate-800 text-white"
                      : "bg-emerald-600 text-white"
                  }`}
                >
                  {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                </div>

                {/* Message Bubble */}
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
                    isUser
                      ? "bg-slate-900 text-white rounded-tr-none"
                      : "bg-white text-slate-800 border border-slate-200/80 rounded-tl-none"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                </div>
              </div>
            );
          })
        )}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="flex items-start space-x-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-600 text-white shadow-sm">
              <Bot className="h-4 w-4 animate-pulse" />
            </div>
            <div className="rounded-2xl rounded-tl-none border border-slate-200 bg-white px-4 py-3 text-sm text-slate-500 shadow-sm flex items-center space-x-2">
              <Sparkles className="h-4 w-4 text-emerald-600 animate-spin" />
              <span className="text-xs">
                Agent A diagnosing state &bull; Verifier checking constraints &bull; Agent B scaffolding...
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </main>

      {/* Input Bar */}
      <footer className="shrink-0 border-t border-slate-200 bg-white p-4">
        <div className="max-w-4xl mx-auto">
          <form
            onSubmit={handleSendMessage}
            className="flex items-end space-x-2 rounded-xl border border-slate-300 bg-white p-2 shadow-sm focus-within:border-indigo-500 focus-within:ring-1 focus-within:ring-indigo-500"
          >
            <textarea
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question or explain your reasoning... (Enter to send, Shift+Enter for newline)"
              rows={2}
              disabled={isLoading}
              className="flex-1 resize-none bg-transparent px-2 py-1 text-sm text-slate-900 placeholder-slate-400 focus:outline-none disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={isLoading || !inputMessage.trim()}
              className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-40 transition shadow-sm"
              title="Send message"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
          <div className="mt-2 flex justify-between items-center text-[11px] text-slate-400 px-1">
            <span>Socratic tutor enforces hidden cognitive state constraints.</span>
            {sessionId && (
              <span className="font-mono text-slate-400 truncate max-w-[200px]" title={sessionId}>
                Session: {sessionId.slice(0, 8)}...
              </span>
            )}
          </div>
        </div>
      </footer>

      {/* Phase 8 Debug Panel Drawer */}
      <DebugPanel
        isOpen={isDebugOpen}
        onClose={() => setIsDebugOpen(false)}
        sessionId={sessionId}
        conceptGraph={conceptGraph}
        activeSnapshot={activeSnapshot}
      />
    </div>
  );
}
