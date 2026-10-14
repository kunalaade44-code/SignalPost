import React from 'react';
import {
  ShieldCheck,
  Database,
  Clock,
  Server,
} from 'lucide-react';
import type { SystemStats } from '../types';

interface SettingsViewProps {
  stats: SystemStats | null;
  isHealthy: boolean;
  supabaseConfigured: boolean;
}

export const SettingsView: React.FC<SettingsViewProps> = ({
  stats,
  isHealthy,
  supabaseConfigured,
}) => {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-in fade-in duration-300">
      <div>
        <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white">System &amp; Settings</h2>
        <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 mt-1">
          Technical configuration, data provenance sources, and compliance budgets.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Data Provenance & Legal */}
        <div className="p-6 rounded-2xl glass-panel space-y-4 border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center gap-2 text-indigo-600 dark:text-indigo-400">
            <ShieldCheck className="w-5 h-5" />
            <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider">
              Data Sources &amp; Licensing
            </h3>
          </div>
          <div className="space-y-3 text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
            <p>
              All primary legal entity data and annual financial statements are retrieved from official Norwegian public registers:
            </p>
            <ul className="list-disc pl-5 space-y-1 text-slate-600 dark:text-slate-400">
              <li>
                <strong className="text-slate-900 dark:text-slate-200">Enhetsregisteret Open API</strong> (Legal names, status, NACE codes, registered roles, address)
              </li>
              <li>
                <strong className="text-slate-900 dark:text-slate-200">Regnskapsregisteret Open API</strong> (Verbatim 3-year annual financial accounts)
              </li>
            </ul>
            <p className="pt-2 text-[11px] text-slate-500 border-t border-slate-200 dark:border-slate-800">
              Licensed under Norsk lisens for offentlige data (NLOD 2.0) provided by Brønnøysundregistrene.
            </p>
          </div>
        </div>

        {/* Database & Storage Architecture */}
        <div className="p-6 rounded-2xl glass-panel space-y-4 border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400">
            <Database className="w-5 h-5" />
            <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider">
              Storage Architecture
            </h3>
          </div>
          <div className="space-y-3 text-xs text-slate-700 dark:text-slate-300">
            <div className="flex items-center justify-between py-1.5 border-b border-slate-200 dark:border-slate-800">
              <span className="text-slate-600 dark:text-slate-400">Local Primary Store</span>
              <span className="font-mono text-emerald-600 dark:text-emerald-400 font-semibold">SQLite (signalpost.db)</span>
            </div>
            <div className="flex items-center justify-between py-1.5 border-b border-slate-200 dark:border-slate-800">
              <span className="text-slate-600 dark:text-slate-400">Cloud Sync Status</span>
              <span className="font-mono text-slate-900 dark:text-white font-semibold">
                {supabaseConfigured ? 'Active & Synced' : 'Optional (Local SQLite only)'}
              </span>
            </div>
            <div className="flex items-center justify-between py-1.5 border-b border-slate-200 dark:border-slate-800">
              <span className="text-slate-600 dark:text-slate-400">Registry Cache TTL</span>
              <span className="font-mono text-slate-700 dark:text-slate-200">7 Days</span>
            </div>
            <div className="flex items-center justify-between py-1.5">
              <span className="text-slate-600 dark:text-slate-400">Website Cache TTL</span>
              <span className="font-mono text-slate-700 dark:text-slate-200">30 Days</span>
            </div>
          </div>
        </div>

        {/* Runtime & Execution Caps */}
        <div className="p-6 rounded-2xl glass-panel space-y-4 border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center gap-2 text-indigo-600 dark:text-indigo-400">
            <Clock className="w-5 h-5" />
            <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider">
              Budget &amp; Safety Limits
            </h3>
          </div>
          <div className="space-y-3 text-xs text-slate-700 dark:text-slate-300">
            <div className="flex items-center justify-between py-1.5 border-b border-slate-200 dark:border-slate-800">
              <span className="text-slate-600 dark:text-slate-400">Max Outbound Requests</span>
              <span className="font-mono text-slate-900 dark:text-white font-semibold">2,000 requests / 100 companies</span>
            </div>
            <div className="flex items-center justify-between py-1.5 border-b border-slate-200 dark:border-slate-800">
              <span className="text-slate-600 dark:text-slate-400">Max Declared Cost</span>
              <span className="font-mono text-slate-900 dark:text-white font-semibold">$10.00 USD cap</span>
            </div>
            <div className="flex items-center justify-between py-1.5 border-b border-slate-200 dark:border-slate-800">
              <span className="text-slate-600 dark:text-slate-400">Execution Timeout</span>
              <span className="font-mono text-slate-900 dark:text-white font-semibold">45 Minutes</span>
            </div>
            <div className="flex items-center justify-between py-1.5">
              <span className="text-slate-600 dark:text-slate-400">Per-Company Budget</span>
              <span className="font-mono text-slate-900 dark:text-white font-semibold">18 requests max</span>
            </div>
          </div>
        </div>

        {/* Service Connectivity */}
        <div className="p-6 rounded-2xl glass-panel space-y-4 border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center gap-2 text-amber-600 dark:text-amber-400">
            <Server className="w-5 h-5" />
            <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider">
              Service Connectivity
            </h3>
          </div>
          <div className="space-y-3 text-xs text-slate-700 dark:text-slate-300">
            <div className="flex items-center justify-between py-1.5 border-b border-slate-200 dark:border-slate-800">
              <span className="text-slate-600 dark:text-slate-400">FastAPI REST Server</span>
              <span className="inline-flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-semibold">
                <span className="w-2 h-2 rounded-full bg-emerald-500 dark:bg-emerald-400" />
                <span>Operational</span>
              </span>
            </div>
            <div className="flex items-center justify-between py-1.5 border-b border-slate-200 dark:border-slate-800">
              <span className="text-slate-600 dark:text-slate-400">Brreg Open Data API</span>
              <span className="inline-flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-semibold">
                <span className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-emerald-500 dark:bg-emerald-400' : 'bg-rose-500'}`} />
                <span>{isHealthy ? 'Reachable' : 'Degraded'}</span>
              </span>
            </div>
            <div className="flex items-center justify-between py-1.5">
              <span className="text-slate-600 dark:text-slate-400">Total Indexed Profiles</span>
              <span className="font-mono font-bold text-slate-900 dark:text-white">
                {stats?.database?.total_profiles ?? 0}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
