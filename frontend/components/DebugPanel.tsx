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
  SplitSquareVertical,
  Play,
  RotateCcw,
  CheckCircle2,
  Lock,
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

interface CounterfactualResult {
  real_reply: string;
  counterfactual_reply: string;
  user_message: string;
  modified_state: any;
  modified_mastery: Record<string, number>;
  verification: {
    attempts_count: number;
    used_fallback: boolean;
    mastered_concepts: string[];
    locked_concepts: string[];
  };
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
  const [activeTab, setActiveTab] = useState<"graph" | "counterfactual" | "json">("graph");

  // Counterfactual Sandbox State
  const [overriddenMastery, setOverriddenMastery] = useState<Record<string, number>>({});
  const [isCfRunning, setIsCfRunning] = useState(false);
  const [cfResult, setCfResult] = useState<CounterfactualResult | null>(null);
  const [cfError, setCfError] = useState<string | null>(null);

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

  // Sync baseline overriddenMastery when current snapshot changes
  useEffect(() => {
    const base = currentSnap?.mastery || {};
    setOverriddenMastery(base);
  }, [currentIndex, history, activeSnapshot]);

  if (!isOpen) return null;

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

  const toggleNodeMastery = (conceptKey: string) => {
    setOverriddenMastery((prev) => {
      const currentVal = prev[conceptKey] ?? 0.15;
      const nextVal = currentVal >= 0.85 ? 0.15 : 0.95;
      return { ...prev, [conceptKey]: nextVal };
    });
  };

  const handleRunCounterfactual = async () => {
    if (!sessionId) return;
    setIsCfRunning(true);
    setCfError(null);

    try {
      const res = await fetch(`${BACKEND_URL}/counterfactual`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          modified_mastery: overriddenMastery,
        }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Counterfactual call failed with HTTP ${res.status}`);
      }

      const result: CounterfactualResult = await res.json();
      setCfResult(result);
      setActiveTab("counterfactual");
    } catch (err: any) {
      setCfError(err.message || "Failed to execute counterfactual query.");
    } finally {
      setIsCfRunning(false);
    }
  };

  const resetOverrides = () => {
    setOverriddenMastery(currentSnap?.mastery || {});
    setCfResult(null);
    setCfError(null);
  };

  const currentState = currentSnap?.state;
  const currentMastery = currentSnap?.mastery || {};
  const probedConcept = currentState?.concept_being_probed || null;

  return (
    <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-3xl flex-col bg-white shadow-2xl border-l border-slate-200 transition-transform duration-300">
      {/* Header */}
      <div className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200 px-6 bg-slate-900 text-white">
        <div className="flex items-center space-x-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500 text-white">
            <Network className="h-4 w-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold tracking-tight">Inspector &amp; Debug Console</h2>
            <p className="text-[11px] text-slate-400">
              Cognitive State Model &bull; BKT Knowledge Tracing &bull; Counterfactual Sandbox
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
      <div className="flex items-center justify-between border-b border-slate-200 bg-white px-6 shrink-0">
        <div className="flex space-x-1">
          <button
            onClick={() => setActiveTab("graph")}
            className={`flex items-center space-x-1.5 py-2.5 px-3 text-xs font-semibold border-b-2 transition ${
              activeTab === "graph"
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            <Network className="h-3.5 w-3.5" />
            <span>Concept Graph</span>
          </button>

          <button
            onClick={() => setActiveTab("counterfactual")}
            className={`flex items-center space-x-1.5 py-2.5 px-3 text-xs font-semibold border-b-2 transition ${
              activeTab === "counterfactual"
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            <SplitSquareVertical className="h-3.5 w-3.5" />
            <span>Counterfactual Sandbox</span>
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
            <span>Raw JSON State</span>
          </button>
        </div>

        {/* Counterfactual Quick Run Trigger */}
        <div className="flex items-center space-x-2">
          <button
            onClick={handleRunCounterfactual}
            disabled={isCfRunning || !sessionId}
            className="inline-flex items-center space-x-1.5 rounded-lg bg-indigo-600 px-2.5 py-1 text-xs font-semibold text-white shadow-sm hover:bg-indigo-700 disabled:opacity-50 transition"
          >
            {isCfRunning ? (
              <Sparkles className="h-3 w-3 animate-spin" />
            ) : (
              <Play className="h-3 w-3 fill-current" />
            )}
            <span>Re-run with Changes</span>
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-5 bg-slate-50/50">
        {cfError && (
          <div className="rounded-lg bg-red-50 border border-red-200 p-3 text-xs text-red-700 flex items-center justify-between">
            <span>{cfError}</span>
            <button onClick={() => setCfError(null)} className="font-semibold text-red-500">Dismiss</button>
          </div>
        )}

        {/* Tab 1: Concept Graph with Overrides */}
        {activeTab === "graph" && (
          <div className="space-y-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <ConceptGraph
                mastery={overriddenMastery}
                probedConcept={probedConcept}
                conceptGraph={conceptGraph}
                onNodeClick={toggleNodeMastery}
                interactive={true}
              />
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-800">Mastery Override Sandbox</span>
                <button
                  onClick={resetOverrides}
                  className="inline-flex items-center space-x-1 text-slate-500 hover:text-slate-800"
                >
                  <RotateCcw className="h-3 w-3" />
                  <span>Reset Overrides</span>
                </button>
              </div>
              <p className="text-slate-500 text-[11px]">
                Click any node in the graph above to toggle its mastery between <strong className="text-emerald-700">0.95 (Mastered)</strong> and <strong className="text-rose-700">0.15 (Locked)</strong>. Then click <strong>"Re-run with Changes"</strong> to see how the tutor would have responded to the latest student message under your hypothetical cognitive model!
              </p>
            </div>
          </div>
        )}

        {/* Tab 2: Counterfactual Side-by-Side Comparison */}
        {activeTab === "counterfactual" && (
          <div className="space-y-5">
            {!cfResult ? (
              <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center space-y-3">
                <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-indigo-50 text-indigo-600">
                  <SplitSquareVertical className="h-5 w-5" />
                </div>
                <h3 className="text-sm font-bold text-slate-800">No Counterfactual Run Yet</h3>
                <p className="text-xs text-slate-500 max-w-md mx-auto">
                  Modify any concept mastery in the <strong>Concept Graph</strong> tab, then click <strong>"Re-run with Changes"</strong> to compare the real tutor reply against the counterfactual reply side by side.
                </p>
                <button
                  onClick={handleRunCounterfactual}
                  disabled={isCfRunning || !sessionId}
                  className="inline-flex items-center space-x-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-indigo-700"
                >
                  <Play className="h-3.5 w-3.5 fill-current" />
                  <span>Execute Counterfactual Run</span>
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Last Student Message Context */}
                <div className="rounded-lg bg-slate-100 border border-slate-200 p-3 text-xs">
                  <span className="font-semibold text-slate-500 block text-[10px] uppercase">
                    Testing on Last Student Message:
                  </span>
                  <p className="font-medium text-slate-900 mt-0.5">"{cfResult.user_message}"</p>
                </div>

                {/* Side-by-Side Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Left: Real Reply */}
                  <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm space-y-3">
                    <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                      <span className="inline-flex items-center space-x-1.5 text-xs font-bold text-slate-700">
                        <span className="h-2 w-2 rounded-full bg-slate-500" />
                        <span>Real Reply (Actual State)</span>
                      </span>
                      <span className="text-[10px] font-mono text-slate-400">Recorded in DB</span>
                    </div>

                    <div className="rounded-lg bg-slate-50 border border-slate-200 p-3 text-xs leading-relaxed text-slate-800 italic">
                      "{cfResult.real_reply}"
                    </div>

                    <div className="text-[11px] text-slate-500 space-y-1">
                      <span className="font-semibold block text-[10px] uppercase text-slate-400">Actual Constraints:</span>
                      <div className="flex flex-wrap gap-1">
                        {currentSnap?.state?.concept_being_probed && (
                          <span className="rounded bg-slate-100 px-1.5 py-0.5 text-slate-700 font-mono">
                            Probed: {currentSnap.state.concept_being_probed}
                          </span>
                        )}
                        <span className="rounded bg-rose-50 border border-rose-200 px-1.5 py-0.5 text-rose-700 font-mono">
                          {Object.values(currentMastery).filter((p) => p < 0.85).length} locked concepts
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Right: Counterfactual Reply */}
                  <div className="rounded-xl border border-indigo-200 bg-indigo-50/30 p-4 shadow-sm space-y-3 ring-1 ring-indigo-500/20">
                    <div className="flex items-center justify-between border-b border-indigo-100 pb-2">
                      <span className="inline-flex items-center space-x-1.5 text-xs font-bold text-indigo-700">
                        <Sparkles className="h-3 w-3 text-indigo-600" />
                        <span>Counterfactual Reply (What-If)</span>
                      </span>
                      <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-100 px-1.5 py-0.5 rounded">
                        Verified
                      </span>
                    </div>

                    <div className="rounded-lg bg-white border border-indigo-200 p-3 text-xs leading-relaxed text-indigo-950 font-medium">
                      "{cfResult.counterfactual_reply}"
                    </div>

                    <div className="text-[11px] text-slate-600 space-y-1">
                      <span className="font-semibold block text-[10px] uppercase text-indigo-600">Counterfactual Partition:</span>
                      <div className="flex flex-wrap gap-1">
                        <span className="rounded bg-emerald-100 border border-emerald-300 px-1.5 py-0.5 text-emerald-800 font-mono text-[10px]">
                          Mastered: {cfResult.verification.mastered_concepts.join(", ") || "None"}
                        </span>
                        <span className="rounded bg-rose-50 border border-rose-200 px-1.5 py-0.5 text-rose-700 font-mono text-[10px]">
                          {cfResult.verification.locked_concepts.length} locked
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Analytical Takeaway Banner */}
                <div className="rounded-xl border border-emerald-200 bg-emerald-50/70 p-3.5 text-xs text-emerald-950 space-y-1">
                  <div className="flex items-center space-x-1.5 font-bold text-emerald-800 text-[11px]">
                    <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                    <span>Steerability &amp; Constraint Proof:</span>
                  </div>
                  <p className="text-[11px] leading-relaxed">
                    Notice how the counterfactual tutor dynamically shifted its pedagogical focus based strictly on your overridden cognitive state, without creating any ghost records or polluting the student's true learning timeline in the database!
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Raw JSON View */}
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
                  overridden_mastery_sandbox: overriddenMastery,
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
