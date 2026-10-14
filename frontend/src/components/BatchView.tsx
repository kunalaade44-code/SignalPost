import React, { useState, useEffect } from 'react';
import {
  Play,
  RotateCcw,
  Clock,
  Send,
  DollarSign,
  ExternalLink,
} from 'lucide-react';
import type { BatchRunState } from '../types';

interface BatchViewProps {
  onSelectOrgnr: (orgnr: string) => void;
}

export const BatchView: React.FC<BatchViewProps> = ({ onSelectOrgnr }) => {
  const [inputText, setInputText] = useState(
    '923609016\n984851006\n976967631\n917088713\n938708606'
  );
  const [concurrency, setConcurrency] = useState(6);
  const [forceRefresh, setForceRefresh] = useState(false);
  const [runState, setRunState] = useState<BatchRunState | null>(null);
  const [isStarting, setIsStarting] = useState(false);

  // SSE event stream listener
  useEffect(() => {
    if (!runState || runState.status === 'COMPLETED' || runState.status === 'FAILED') {
      return;
    }

    const eventSource = new EventSource(`/api/runs/${runState.run_id}`);

    eventSource.onmessage = (event) => {
      try {
        const data: BatchRunState = JSON.parse(event.data);
        setRunState(data);
        if (data.status === 'COMPLETED' || data.status === 'FAILED') {
          eventSource.close();
        }
      } catch (err) {
        console.error('SSE parse error:', err);
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [runState?.run_id, runState?.status]);

  const handleStartBatch = async () => {
    const rawList = inputText
      .split('\n')
      .map((s) => s.trim())
      .filter((s) => s.length > 0 && !s.startsWith('#'));

    if (rawList.length === 0) return;

    setIsStarting(true);
    try {
      const resp = await fetch('/api/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          org_numbers: rawList,
          concurrency,
          force_refresh: forceRefresh,
        }),
      });

      if (resp.ok) {
        const data = await resp.json();
        setRunState({
          run_id: data.run_id,
          status: 'QUEUED',
          total_companies: data.total_companies,
          processed_count: 0,
          successful_count: 0,
          cached_count: 0,
          failed_count: 0,
          progress_pct: 0.0,
          results: [],
        });
      }
    } catch (err) {
      console.error('Failed to start batch:', err);
    } finally {
      setIsStarting(false);
    }
  };

  const handleLoadSample1000 = () => {
    // Generate sample list
    const samples = [
      '811599492', '812467182', '813390922', '813521792', '813646552',
      '813822962', '814968952', '816022932', '818334532', '818874502',
      '923609016', '984851006', '976967631', '917088713', '938708606',
    ];
    setInputText(samples.join('\n'));
  };

  const completedCount = Math.min(runState?.processed_count || 0, runState?.total_companies || 0);
  const requestsUsed = completedCount * 3;
  const costUsed = completedCount * 0.0002;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-in fade-in duration-300">
      {/* Title */}
      <div>
        <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white">Batch Agent Runner</h2>
        <p className="text-slate-600 dark:text-slate-400 text-sm mt-1">
          Profile multiple companies simultaneously with global budget constraints and live SSE tracking.
        </p>
      </div>

      {/* Budget Gauges (Section 1 Limits) */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Requests meter */}
        <div className="p-5 rounded-2xl glass-panel relative overflow-hidden border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center justify-between text-xs text-slate-600 dark:text-slate-400 mb-2 font-medium">
            <span className="flex items-center gap-1.5">
              <Send className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
              <span>Outbound Requests Budget</span>
            </span>
            <span className="font-mono text-slate-900 dark:text-white font-bold">
              {requestsUsed} / 2,000
            </span>
          </div>
          <div className="w-full h-2 rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
            <div
              className="h-full bg-indigo-500 rounded-full transition-all duration-300"
              style={{ width: `${Math.min(100, (requestsUsed / 2000) * 100)}%` }}
            />
          </div>
          <span className="text-[11px] text-slate-500 dark:text-slate-400 mt-2 block">
            Limit: 2,000 requests per 100 companies daily test
          </span>
        </div>

        {/* Cost meter */}
        <div className="p-5 rounded-2xl glass-panel relative overflow-hidden border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center justify-between text-xs text-slate-600 dark:text-slate-400 mb-2 font-medium">
            <span className="flex items-center gap-1.5">
              <DollarSign className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              <span>Declared API Cost</span>
            </span>
            <span className="font-mono text-emerald-600 dark:text-emerald-400 font-bold">
              ${costUsed.toFixed(4)} / $10.00
            </span>
          </div>
          <div className="w-full h-2 rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
            <div
              className="h-full bg-emerald-500 rounded-full transition-all duration-300"
              style={{ width: `${Math.min(100, (costUsed / 10.0) * 100)}%` }}
            />
          </div>
          <span className="text-[11px] text-slate-500 dark:text-slate-400 mt-2 block">
            Target &lt; $0.50 via Mistral Free Tier &amp; Open Registry
          </span>
        </div>

        {/* Time meter */}
        <div className="p-5 rounded-2xl glass-panel relative overflow-hidden border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center justify-between text-xs text-slate-600 dark:text-slate-400 mb-2 font-medium">
            <span className="flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-amber-500 dark:text-amber-400" />
              <span>Wall-Clock Deadline</span>
            </span>
            <span className="font-mono text-amber-600 dark:text-amber-400 font-bold">
              {runState?.duration_seconds ? `${runState.duration_seconds}s` : '0s'} / 2,700s
            </span>
          </div>
          <div className="w-full h-2 rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
            <div
              className="h-full bg-amber-500 rounded-full transition-all duration-300"
              style={{
                width: `${Math.min(
                  100,
                  ((runState?.duration_seconds || 0) / 2700) * 100
                )}%`,
              }}
            />
          </div>
          <span className="text-[11px] text-slate-500 dark:text-slate-400 mt-2 block">
            Limit: 45 minutes (2,700s) with graceful degradation
          </span>
        </div>
      </div>

      {/* Input Configuration & Launcher */}
      <div className="p-6 rounded-2xl glass-panel space-y-6 border border-slate-200 dark:border-slate-800 shadow-sm">
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-semibold text-slate-700 dark:text-slate-200">
              Target Organization Numbers (1 per line)
            </label>
            <button
              onClick={handleLoadSample1000}
              className="text-xs text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 font-medium cursor-pointer"
            >
              + Load Sample Batch List
            </button>
          </div>
          <textarea
            rows={5}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="923609016&#10;984851006&#10;..."
            className="w-full rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 p-3 font-mono text-xs text-slate-900 dark:text-white placeholder:text-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-indigo-500 shadow-sm"
          />
        </div>

        <div className="flex flex-wrap items-center justify-between gap-4 pt-2">
          {/* Concurrency slider */}
          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">Concurrency Workers:</span>
            <input
              type="range"
              min={1}
              max={12}
              value={concurrency}
              onChange={(e) => setConcurrency(Number(e.target.value))}
              className="accent-indigo-500 cursor-pointer"
            />
            <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-xs font-bold text-slate-900 dark:text-white font-mono border border-slate-200 dark:border-slate-700">
              {concurrency}
            </span>
          </div>

          <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400 cursor-pointer">
            <input
              type="checkbox"
              checked={forceRefresh}
              onChange={(e) => setForceRefresh(e.target.checked)}
              className="rounded bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-700 text-indigo-600"
            />
            <span>Force Re-crawl (Bypass Cache)</span>
          </label>

          <button
            onClick={handleStartBatch}
            disabled={isStarting || runState?.status === 'RUNNING'}
            className={`flex items-center gap-2 px-6 py-2.5 rounded-xl font-semibold text-sm transition-all cursor-pointer ${
              runState?.status === 'RUNNING'
                ? 'bg-slate-200 dark:bg-slate-800 text-slate-400 dark:text-slate-500 cursor-not-allowed'
                : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30'
            }`}
          >
            {runState?.status === 'RUNNING' ? (
              <>
                <RotateCcw className="w-4 h-4 animate-spin" />
                <span>Running Batch...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                <span>Launch Batch Profiling</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Live Progress Bar & Results Stream */}
      {runState && (
        <div className="p-6 rounded-2xl glass-panel space-y-6 border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-slate-900 dark:text-white">Run ID:</span>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-indigo-700 dark:text-indigo-300 border border-slate-200 dark:border-slate-700">
                {runState.run_id}
              </span>
              <span
                className={`text-xs px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                  runState.status === 'COMPLETED'
                    ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/30'
                    : runState.status === 'RUNNING'
                    ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/30 animate-pulse'
                    : 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300'
                }`}
              >
                {runState.status}
              </span>
            </div>

            <span className="text-sm font-bold text-slate-900 dark:text-white">
              {Math.min(runState.processed_count, runState.total_companies)} / {runState.total_companies} Companies (
              {Math.min(100, Math.max(0, runState.progress_pct)).toFixed(1)}%)
            </span>
          </div>

          {/* Progress bar */}
          <div className="w-full h-3 rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-emerald-400 transition-all duration-300"
              style={{ width: `${Math.min(100, Math.max(0, runState.progress_pct))}%` }}
            />
          </div>

          {/* Results table */}
          <div>
            <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">
              Completed Companies in this Run
            </h4>

            <div className="overflow-x-auto max-h-80 overflow-y-auto">
              <table className="w-full text-left text-sm text-slate-700 dark:text-slate-300">
                <thead className="text-xs uppercase bg-slate-100 dark:bg-slate-800/60 text-slate-700 dark:text-slate-400 sticky top-0 border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="px-4 py-2.5">Org Number</th>
                    <th className="px-4 py-2.5">Legal Name</th>
                    <th className="px-4 py-2.5">Status</th>
                    <th className="px-4 py-2.5">Source</th>
                    <th className="px-4 py-2.5 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                  {runState.results.map((r, idx) => (
                    <tr key={idx} className="hover:bg-slate-100/70 dark:hover:bg-slate-800/40">
                      <td className="px-4 py-2.5 font-mono text-xs text-indigo-600 dark:text-indigo-300 font-bold">
                        {r.org_number}
                      </td>
                      <td className="px-4 py-2.5 font-medium text-slate-900 dark:text-white">{r.legal_name}</td>
                      <td className="px-4 py-2.5 text-xs">
                        <span
                          className={`px-2 py-0.5 rounded font-semibold ${
                            r.status === 'ACTIVE'
                              ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20'
                              : 'bg-rose-50 text-rose-700 dark:bg-rose-500/10 dark:text-rose-400 border border-rose-200 dark:border-rose-500/20'
                          }`}
                        >
                          {r.status}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-xs text-slate-600 dark:text-slate-400">
                        {r.cached ? 'Database Cache' : 'Live Crawl'}
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        <button
                          onClick={() => onSelectOrgnr(r.org_number)}
                          className="inline-flex items-center gap-1 text-xs text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 font-medium cursor-pointer"
                        >
                          <span>Open Profile</span>
                          <ExternalLink className="w-3 h-3" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
