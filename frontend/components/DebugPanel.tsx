"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  History,
  Code2,
  Network,
  ChevronLeft,
  ChevronRight,
  Radio,
  Clock,
  Sparkles,
  AlertTriangle,
  Lightbulb,
} from "lucide-react";
import ConceptGraph from "./ConceptGraph";

export interface SnapshotItem {
  id: string;
  session_id: string;
  message_id: string;
  state: {
    concept_being_probed: string;
    observed_outcome: string;
    current_misconceptions: Array<{ concept: string; description: string }>;
    frustration_level: number;
    suggested_scaffolding_strategy: string;
  };
  mastery: Record<string, number>;
  created_at: string;
}

interface DebugPanelProps {
  isOpen: boolean;
  onClose: () => void;
  sessionId: string | null;
  conceptGraph: Record<string, { prereqs: string[] }>;
  activeSnapshot: SnapshotItem | null;
}

const BACKEND_URL = "http://127.0.0.1:8000";

export default function DebugPanel({
  isOpen,
  onClose,
  sessionId,
  conceptGraph,
  activeSnapshot,
}: DebugPanelProps) {
  const [history, setHistory] = useState<SnapshotItem[]>([]);
  const [currentIndex, setCurrentIndex] = useState<number>(-1);
  const [isLiveMode, setIsLiveMode] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<"graph" | "json">("graph");

  // Fetch history when panel opens or when active snapshot changes
  useEffect(() => {
    if (!sessionId || !isOpen) return;

    const fetchHistory = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/state/${sessionId}/history`);
        if (res.ok) {
          const data = await res.json();
          const snaps: SnapshotItem[] = data.history || [];
          setHistory(snaps);
          if (isLiveMode || currentIndex === -1) {
            setCurrentIndex(snaps.length - 1);
          }
        }
      } catch (err) {
        console.error("Failed to load snapshot history", err);
      }
    };

    fetchHistory();
  }, [sessionId, isOpen, activeSnapshot, isLiveMode]);

  if (!isOpen) return null;

  // Selected snapshot to view (either historical scrub or live)
  const currentSnap: SnapshotItem | null =
    history.length > 0 && currentIndex >= 0 && currentIndex < history.length
      ? history[currentIndex]
      : activeSnapshot;

  const totalSnapshots = history.length;
  const isViewingLive = isLiveMode || currentIndex === totalSnapshots - 1;

  const handleScrub = (idx: number) => {
    const clamped = Math.max(0, Math.min(totalSnapshots - 1, idx));
    setCurrentIndex(clamped);
    setIsLiveMode(clamped === totalSnapshots - 1);
  };

  const handleLiveToggle = () => {
    setIsLiveMode(true);
    setCurrentIndex(totalSnapshots - 1);
  };

  const currentState = currentSnap?.state;
  const currentMastery = currentSnap?.mastery || {};
  const probedConcept = currentState?.concept_being_probed || null;

  return (
    <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-2xl flex-col bg-white shadow-2xl border-l border-slate-200 transition-transform duration-300">
      {/* Header */}
      <div className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200 px-6 bg-slate-900 text-white">
        <div className="flex items-center space-x-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500 text-white">
            <Network className="h-4 w-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold tracking-tight">Inspector &amp; Debug Console</h2>
            <p className="text-[11px] text-slate-400">
              Cognitive State Model &bull; BKT Knowledge Tracing &bull; Scrubber
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleLiveToggle}
            className={`inline-flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-semibold transition ${
              isViewingLive
                ? "bg-emerald-500 text-white"
                : "bg-slate-800 text-slate-300 hover:bg-slate-700"
            }`}
          >
            <Radio className={`h-3 w-3 ${isViewingLive ? "animate-pulse" : ""}`} />
            <span>Live Stream</span>
          </button>

          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white transition"
            title="Close Panel"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* History Scrubber Controls */}
      <div className="border-b border-slate-200 bg-slate-50 px-6 py-3 shrink-0">
        <div className="flex items-center justify-between text-xs text-slate-600 mb-2">
          <div className="flex items-center space-x-1.5 font-medium">
            <History className="h-3.5 w-3.5 text-indigo-600" />
            <span>Turn-by-Turn History Scrubber:</span>
            <span className="font-bold text-slate-900">
              Turn {currentIndex + 1} of {totalSnapshots || 1}
            </span>
          </div>

          {currentSnap?.created_at && (
            <div className="flex items-center space-x-1 text-[11px] text-slate-400 font-mono">
              <Clock className="h-3 w-3" />
              <span>{new Date(currentSnap.created_at).toLocaleTimeString()}</span>
            </div>
          )}
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={() => handleScrub(currentIndex - 1)}
            disabled={currentIndex <= 0}
            className="rounded p-1 text-slate-600 hover:bg-slate-200 disabled:opacity-30 transition"
            title="Step Back 1 Turn"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>

          <input
            type="range"
            min={0}
            max={Math.max(0, totalSnapshots - 1)}
            value={Math.max(0, currentIndex)}
            onChange={(e) => handleScrub(parseInt(e.target.value, 10))}
            disabled={totalSnapshots <= 1}
            className="w-full accent-indigo-600 cursor-pointer disabled:opacity-40"
          />

          <button
            onClick={() => handleScrub(currentIndex + 1)}
            disabled={currentIndex >= totalSnapshots - 1}
            className="rounded p-1 text-slate-600 hover:bg-slate-200 disabled:opacity-30 transition"
            title="Step Forward 1 Turn"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Mode Navigation Tabs */}
      <div className="flex border-b border-slate-200 bg-white px-6 shrink-0">
        <button
          onClick={() => setActiveTab("graph")}
          className={`flex items-center space-x-1.5 py-2.5 px-3 text-xs font-semibold border-b-2 transition ${
            activeTab === "graph"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <Network className="h-3.5 w-3.5" />
          <span>Concept Mastery Graph</span>
        </button>
        <button
          onClick={() => setActiveTab("json")}
          className={`flex items-center space-x-1.5 py-2.5 px-3 text-xs font-semibold border-b-2 transition ${
            activeTab === "json"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <Code2 className="h-3.5 w-3.5" />
          <span>Raw Cognitive JSON</span>
        </button>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-5 bg-slate-50/50">
        {/* State Summary Banner */}
        {currentState && (
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Turn Cognitive Diagnostic
              </span>
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold ${
                  currentState.observed_outcome === "correct"
                    ? "bg-emerald-100 text-emerald-800"
                    : currentState.observed_outcome === "partially_correct"
                    ? "bg-amber-100 text-amber-800"
                    : "bg-rose-100 text-rose-800"
                }`}
              >
                {currentState.observed_outcome.replace(/_/g, " ").toUpperCase()}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="rounded-lg bg-slate-50 p-2.5 border border-slate-200">
                <span className="text-slate-500 block text-[10px] uppercase font-semibold">Probed Concept</span>
                <span className="font-bold text-slate-800 capitalize">
                  {currentState.concept_being_probed.replace(/_/g, " ")}
                </span>
              </div>
              <div className="rounded-lg bg-slate-50 p-2.5 border border-slate-200">
                <span className="text-slate-500 block text-[10px] uppercase font-semibold">Frustration Level</span>
                <span className="font-bold text-slate-800">
                  {(currentState.frustration_level * 100).toFixed(0)}%
                </span>
              </div>
            </div>

            {/* Misconceptions Callout */}
            {currentState.current_misconceptions?.length > 0 && (
              <div className="rounded-lg bg-amber-50/80 border border-amber-200 p-2.5 text-xs text-amber-900 space-y-1">
                <div className="flex items-center space-x-1.5 font-bold text-amber-800 text-[11px]">
                  <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />
                  <span>Diagnosed Misconception:</span>
                </div>
                {currentState.current_misconceptions.map((m, i) => (
                  <p key={i} className="text-xs leading-relaxed pl-5">
                    &bull; <span className="font-semibold capitalize">{m.concept.replace(/_/g, " ")}</span>: {m.description}
                  </p>
                ))}
              </div>
            )}

            {/* Scaffolding Strategy */}
            {currentState.suggested_scaffolding_strategy && (
              <div className="rounded-lg bg-indigo-50/80 border border-indigo-200 p-2.5 text-xs text-indigo-900 space-y-1">
                <div className="flex items-center space-x-1.5 font-bold text-indigo-800 text-[11px]">
                  <Lightbulb className="h-3.5 w-3.5 text-indigo-600" />
                  <span>Agent A Recommended Scaffolding:</span>
                </div>
                <p className="text-xs leading-relaxed pl-5">
                  {currentState.suggested_scaffolding_strategy}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Tab 1: Concept Graph */}
        {activeTab === "graph" && (
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <ConceptGraph
              mastery={currentMastery}
              probedConcept={probedConcept}
              conceptGraph={conceptGraph}
            />
          </div>
        )}

        {/* Tab 2: Raw JSON View */}
        {activeTab === "json" && (
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-4 shadow-sm text-xs font-mono text-emerald-400 overflow-x-auto">
            <div className="flex justify-between items-center text-slate-400 text-[10px] pb-2 border-b border-slate-800 mb-2">
              <span>SNAPSHOT ID: {currentSnap?.id || "N/A"}</span>
              <span>MESSAGE ID: {currentSnap?.message_id?.slice(0, 8)}...</span>
            </div>
            <pre className="whitespace-pre-wrap leading-relaxed">
              {JSON.stringify(
                {
                  cognitive_state: currentState,
                  mastery_probabilities: currentMastery,
                },
                null,
                2
              )}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
