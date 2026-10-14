import React, { useState, useEffect } from 'react';
import { Clock, FileDiff, ArrowRight } from 'lucide-react';
import type { HistoryRevision } from '../types';

interface HistoryViewProps {
  initialOrgnr?: string;
  onSelectOrgnr: (orgnr: string) => void;
}

export const HistoryView: React.FC<HistoryViewProps> = ({ initialOrgnr, onSelectOrgnr }) => {
  const [orgnrInput, setOrgnrInput] = useState(initialOrgnr || '923609016');
  const [revisions, setRevisions] = useState<HistoryRevision[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = async (targetNr: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await fetch(`/api/company/${targetNr}/history`);
      if (resp.ok) {
        const data = await resp.json();
        setRevisions(data.revisions || []);
      } else {
        setError('No history records found for this organization.');
        setRevisions([]);
      }
    } catch (err) {
      setError('Failed to fetch history.');
      setRevisions([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (initialOrgnr) {
      setOrgnrInput(initialOrgnr);
      fetchHistory(initialOrgnr);
    } else {
      fetchHistory('923609016');
    }
  }, [initialOrgnr]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (orgnrInput.trim()) {
      fetchHistory(orgnrInput.trim());
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-in fade-in duration-300">
      <div>
        <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white">Company Audit &amp; Diff History</h2>
        <p className="text-slate-600 dark:text-slate-400 text-sm mt-1">
          Full version-controlled audit trail tracking every fact change, revision hash, and update reason over time.
        </p>
      </div>

      {/* Search Bar & Actions */}
      <div className="flex flex-wrap items-center gap-4">
        <form onSubmit={handleSearch} className="max-w-xl flex-1">
          <div className="flex items-center gap-2 p-2 rounded-xl glass-panel border border-slate-200 dark:border-slate-800 shadow-sm">
            <input
              type="text"
              value={orgnrInput}
              onChange={(e) => setOrgnrInput(e.target.value)}
              placeholder="Search history by org number (e.g. 923609016)"
              className="w-full bg-transparent text-slate-900 dark:text-white px-3 py-1.5 text-sm focus:outline-none font-mono placeholder:text-slate-400 dark:placeholder-slate-500"
            />
            <button
              type="submit"
              className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold cursor-pointer shadow-sm"
            >
              Load History
            </button>
          </div>
        </form>

        {orgnrInput && (
          <button
            onClick={() => onSelectOrgnr(orgnrInput.trim())}
            className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-semibold border border-slate-200 dark:border-slate-700 transition-colors shadow-sm cursor-pointer"
          >
            <span>View Full Profile</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Revision List */}
      <div className="space-y-4">
        {isLoading && <div className="text-center py-12 text-slate-500 dark:text-slate-400">Loading audit history...</div>}

        {error && <div className="text-center py-8 text-amber-600 dark:text-amber-400 text-sm font-medium">{error}</div>}

        {!isLoading && revisions.length === 0 && !error && (
          <div className="text-center py-12 text-slate-500 dark:text-slate-400 text-sm">
            No revisions found for {orgnrInput}.
          </div>
        )}

        {revisions.map((rev) => (
          <div
            key={rev.id}
            className="p-5 rounded-2xl glass-panel hover:border-indigo-500/50 border border-slate-200 dark:border-slate-800 shadow-sm transition-all space-y-3"
          >
            <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <FileDiff className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                <span className="font-mono text-sm font-bold text-slate-900 dark:text-white">{rev.field_name}</span>
                <span className="text-xs px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 font-mono border border-indigo-200 dark:border-indigo-500/20 font-semibold">
                  {rev.revision_ref}
                </span>
              </div>
              <span className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1">
                <Clock className="w-3.5 h-3.5" />
                <span>{new Date(rev.changed_at).toLocaleString()}</span>
              </span>
            </div>

            <p className="text-xs text-slate-700 dark:text-slate-300 font-medium">
              Reason: <span className="text-slate-600 dark:text-slate-400 font-normal">{rev.change_reason}</span>
            </p>

            {/* Old vs New Value Comparison */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
              <div className="p-3 rounded-xl bg-rose-50/60 dark:bg-slate-900/60 border border-rose-200 dark:border-slate-800">
                <span className="text-[10px] uppercase font-bold text-rose-600 dark:text-rose-400 block mb-1">
                  Previous Value
                </span>
                <div className="text-xs font-mono text-slate-600 dark:text-slate-400 break-words">
                  {rev.old_value !== null && rev.old_value !== undefined
                    ? JSON.stringify(rev.old_value)
                    : '(Initial / None)'}
                </div>
              </div>

              <div className="p-3 rounded-xl bg-emerald-50/60 dark:bg-slate-900/60 border border-emerald-200 dark:border-slate-800">
                <span className="text-[10px] uppercase font-bold text-emerald-600 dark:text-emerald-400 block mb-1">
                  Updated Value
                </span>
                <div className="text-xs font-mono text-emerald-800 dark:text-emerald-300 break-words font-semibold">
                  {rev.new_value !== null && rev.new_value !== undefined
                    ? JSON.stringify(rev.new_value)
                    : '(Null)'}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
