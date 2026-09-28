"use client";

import React from "react";
import { Lock, CheckCircle2, Target } from "lucide-react";

interface ConceptGraphProps {
  mastery: Record<string, number>;
  probedConcept?: string | null;
  conceptGraph: Record<string, { prereqs: string[] }>;
}

// Hierarchical layout layers for clean visualization
const LAYERS: string[][] = [
  ["variable", "constant", "coordinate_plane"],
  ["linear_equation", "function"],
  ["slope", "y_intercept", "system_of_equations"],
  ["slope_intercept_form", "rate_of_change"],
];

// Helper to get color classes based on continuous mastery probability
export function getMasteryColor(prob: number = 0.15) {
  if (prob >= 0.85) {
    return {
      bg: "bg-emerald-50",
      border: "border-emerald-500",
      text: "text-emerald-700",
      bar: "bg-emerald-500",
      badgeBg: "bg-emerald-100",
      badgeText: "text-emerald-800",
      label: "Mastered",
    };
  }
  if (prob >= 0.60) {
    return {
      bg: "bg-sky-50",
      border: "border-sky-400",
      text: "text-sky-700",
      bar: "bg-sky-500",
      badgeBg: "bg-sky-100",
      badgeText: "text-sky-800",
      label: "Advancing",
    };
  }
  if (prob >= 0.35) {
    return {
      bg: "bg-amber-50",
      border: "border-amber-400",
      text: "text-amber-700",
      bar: "bg-amber-500",
      badgeBg: "bg-amber-100",
      badgeText: "text-amber-800",
      label: "Developing",
    };
  }
  return {
    bg: "bg-rose-50",
    border: "border-rose-300",
    text: "text-rose-700",
    bar: "bg-rose-400",
    badgeBg: "bg-rose-100",
    badgeText: "text-rose-800",
    label: "Locked",
  };
}

export default function ConceptGraph({
  mastery = {},
  probedConcept,
  conceptGraph = {},
}: ConceptGraphProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between text-xs text-slate-500 pb-1 border-b border-slate-200">
        <span className="font-semibold uppercase tracking-wider">Concept Dependency Ontology</span>
        <div className="flex items-center space-x-2">
          <span className="flex items-center space-x-1">
            <span className="h-2 w-2 rounded-full bg-rose-400" />
            <span>&lt;0.35</span>
          </span>
          <span className="flex items-center space-x-1">
            <span className="h-2 w-2 rounded-full bg-amber-400" />
            <span>0.35-0.6</span>
          </span>
          <span className="flex items-center space-x-1">
            <span className="h-2 w-2 rounded-full bg-sky-500" />
            <span>0.6-0.85</span>
          </span>
          <span className="flex items-center space-x-1">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            <span>&ge;0.85</span>
          </span>
        </div>
      </div>

      {/* Layered Graph Display */}
      <div className="space-y-3">
        {LAYERS.map((layer, layerIdx) => (
          <div key={layerIdx} className="space-y-1">
            <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest px-1">
              {layerIdx === 0
                ? "Foundational Prereqs"
                : layerIdx === 1
                ? "Intermediate Structures"
                : layerIdx === 2
                ? "Core Geometric Concepts"
                : "Composite Target Models"}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {layer.map((conceptKey) => {
                const prob = mastery[conceptKey] ?? 0.15;
                const isProbed = probedConcept === conceptKey;
                const colors = getMasteryColor(prob);
                const prereqs = conceptGraph[conceptKey]?.prereqs || [];

                return (
                  <div
                    key={conceptKey}
                    className={`relative rounded-lg p-2.5 border transition-all duration-200 shadow-sm ${colors.bg} ${colors.border} ${
                      isProbed ? "ring-2 ring-indigo-500 ring-offset-1" : ""
                    }`}
                  >
                    {/* Active Probe Pill */}
                    {isProbed && (
                      <span className="absolute -top-2 right-2 inline-flex items-center space-x-1 rounded-full bg-indigo-600 px-2 py-0.5 text-[9px] font-bold text-white shadow-sm">
                        <Target className="h-2.5 w-2.5 animate-pulse" />
                        <span>PROBING</span>
                      </span>
                    )}

                    <div className="flex items-start justify-between">
                      <div className="truncate">
                        <h4 className="text-xs font-bold text-slate-800 truncate capitalize">
                          {conceptKey.replace(/_/g, " ")}
                        </h4>
                        {prereqs.length > 0 && (
                          <p className="text-[10px] text-slate-500 truncate" title={`Requires: ${prereqs.join(", ")}`}>
                            Reqs: {prereqs.map((p) => p.replace(/_/g, " ")).join(", ")}
                          </p>
                        )}
                      </div>

                      <span
                        className={`inline-flex items-center space-x-1 rounded px-1.5 py-0.5 text-[10px] font-semibold ${colors.badgeBg} ${colors.badgeText}`}
                      >
                        {prob >= 0.85 ? (
                          <CheckCircle2 className="h-3 w-3" />
                        ) : (
                          <Lock className="h-2.5 w-2.5" />
                        )}
                        <span>{(prob * 100).toFixed(1)}%</span>
                      </span>
                    </div>

                    {/* Progress Bar */}
                    <div className="mt-2 h-1.5 w-full rounded-full bg-slate-200/80 overflow-hidden">
                      <div
                        className={`h-full transition-all duration-300 ${colors.bar}`}
                        style={{ width: `${Math.min(100, Math.max(0, prob * 100))}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
