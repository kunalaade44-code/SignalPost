import React from 'react';
import { X, ExternalLink, CheckCircle2, ShieldCheck, Clock, FileText, Info } from 'lucide-react';
import type { Fact } from '../types';

interface EvidenceDrawerProps {
  fact: Fact | null;
  onClose: () => void;
}

export const EvidenceDrawer: React.FC<EvidenceDrawerProps> = ({ fact, onClose }) => {
  if (!fact) return null;

  const confidencePercent = Math.round(fact.confidence * 100);

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/60 backdrop-blur-sm flex justify-end transition-opacity">
      <div className="w-full max-w-xl bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 shadow-2xl h-full flex flex-col p-6 overflow-y-auto animate-in slide-in-from-right duration-300">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-200 dark:border-slate-800">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-500/20">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Why This Fact?</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">Provenance & Verification Evidence</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-white dark:hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="space-y-6 py-6 flex-1">
          {/* Fact Field & Value */}
          <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700/50">
            <span className="text-xs font-mono uppercase text-indigo-600 dark:text-indigo-400 tracking-wider font-semibold">
              {fact.field}
            </span>
            <div className="mt-1 text-xl font-bold text-slate-900 dark:text-white break-words">
              {typeof fact.value === 'object' ? JSON.stringify(fact.value, null, 2) : String(fact.value)}
            </div>
          </div>

          {/* Confidence Score */}
          <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700/50">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider">
                Attribution Confidence
              </span>
              <span className="text-sm font-bold text-emerald-600 dark:text-emerald-400">{confidencePercent}%</span>
            </div>
            <div className="w-full h-2.5 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-emerald-400 transition-all duration-500"
                style={{ width: `${confidencePercent}%` }}
              />
            </div>
          </div>

          {/* Explanation */}
          <div>
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
              <Info className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
              <span>Explanation & Provenance</span>
            </div>
            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800 text-sm text-slate-700 dark:text-slate-200 leading-relaxed">
              {fact.explanation}
            </div>
          </div>

          {/* Verbatim Evidence Snippet */}
          <div>
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
              <FileText className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              <span>Verbatim Evidence Quote</span>
            </div>
            <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 font-mono text-xs text-emerald-800 dark:text-emerald-300 break-words leading-relaxed overflow-x-auto whitespace-pre-wrap">
              {fact.evidence}
            </div>
          </div>

          {/* Match Signals */}
          {fact.match_signals && fact.match_signals.length > 0 && (
            <div>
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block mb-2">
                Independent Match Signals Used
              </span>
              <div className="flex flex-wrap gap-2">
                {fact.match_signals.map((sig, idx) => (
                  <span
                    key={idx}
                    className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/20 text-xs text-indigo-700 dark:text-indigo-300 font-medium"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
                    <span>{sig}</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Source Link & Retrieval Date */}
          <div className="pt-4 border-t border-slate-200 dark:border-slate-800 space-y-3">
            <div>
              <span className="text-xs text-slate-500 dark:text-slate-400 block mb-1">Source URL</span>
              <a
                href={fact.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 text-xs text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 break-all transition-colors font-medium"
              >
                <span>{fact.source_url}</span>
                <ExternalLink className="w-3.5 h-3.5 shrink-0" />
              </a>
            </div>

            <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
              <span className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
                <span>Retrieved: {new Date(fact.retrieved_at).toLocaleString()}</span>
              </span>
              <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-mono text-[11px] border border-slate-200 dark:border-slate-700">
                {fact.source_type}
              </span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="pt-4 border-t border-slate-200 dark:border-slate-800">
          <button
            onClick={onClose}
            className="w-full py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 dark:bg-slate-800 dark:hover:bg-slate-700 text-sm font-semibold dark:text-white transition-colors cursor-pointer border border-slate-200 dark:border-slate-700"
          >
            Close Drawer
          </button>
        </div>
      </div>
    </div>
  );
};
