import React, { useState, useEffect } from 'react';
import {
  CheckCircle2,
  AlertCircle,
  Upload,
  RefreshCw,
  ArrowRight,
  ShieldCheck,
  RotateCcw,
} from 'lucide-react';
import { validateNorwegianOrgNumber } from '../utils/checksum';
import type { CompanyProfile } from '../types';

interface PreviewData {
  org_number: string;
  legal_name: string;
  status: string;
  org_form: string;
  address?: string | null;
  municipality?: string | null;
  is_already_profiled: boolean;
  is_tracked: boolean;
  facts_count: number;
  last_checked_at?: string | null;
}

interface AddCompanyViewProps {
  onProfileComplete: (profile: CompanyProfile) => void;
  showToast: (msg: string) => void;
}

export const AddCompanyView: React.FC<AddCompanyViewProps> = ({
  onProfileComplete,
  showToast,
}) => {
  const [mode, setMode] = useState<'single' | 'search' | 'bulk_text' | 'upload'>('single');

  // Single Orgnr Mode State
  const [singleInput, setSingleInput] = useState('');
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  // Search by Name Mode State
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // Bulk Paste Mode State
  const [bulkInput, setBulkInput] = useState('');

  // Execution & Progress State
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentStep, setCurrentStep] = useState<string>('');
  const [executionError, setExecutionError] = useState<string | null>(null);

  const checksumResult = validateNorwegianOrgNumber(singleInput);

  // Auto-fetch preview when a valid 9-digit orgnr is typed
  useEffect(() => {
    if (checksumResult.isValid) {
      const fetchPreview = async () => {
        setIsPreviewLoading(true);
        setPreviewError(null);
        try {
          const res = await fetch(`/api/companies/${checksumResult.clean}/preview`);
          if (res.ok) {
            const data: PreviewData = await res.json();
            setPreview(data);
          } else {
            setPreview(null);
            setPreviewError('Organization not found in Enhetsregisteret');
          }
        } catch {
          setPreviewError('Failed to connect to Brreg preview');
        } finally {
          setIsPreviewLoading(false);
        }
      };
      fetchPreview();
    } else {
      setPreview(null);
      setPreviewError(null);
    }
  }, [checksumResult.clean, checksumResult.isValid]);

  // Name Search execution
  const handleSearchSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim() || searchQuery.trim().length < 2) return;

    setIsSearching(true);
    try {
      const res = await fetch(`/api/companies/search?q=${encodeURIComponent(searchQuery.trim())}`);
      if (res.ok) {
        const data = await res.json();
        setSearchResults(data.results || []);
        if ((data.results || []).length === 0) {
          showToast('No matching companies found in Brreg');
        }
      }
    } catch {
      showToast('Search request failed');
    } finally {
      setIsSearching(false);
    }
  };

  const handleSelectSearchResult = (nr: string) => {
    setSingleInput(nr);
    setMode('single');
  };

  // Submit Single Company
  const handleConfirmSingle = async (forceRefresh = false) => {
    if (!checksumResult.isValid) return;

    setIsSubmitting(true);
    setExecutionError(null);
    setCurrentStep('Connecting to Brønnøysundregistrene official open data...');

    try {
      setTimeout(() => setCurrentStep('Crawling official web presence and verifying match signals...'), 800);
      setTimeout(() => setCurrentStep('Synthesizing verified facts and annual financial records...'), 1600);

      const res = await fetch('/api/companies', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          org_number: checksumResult.clean,
          force_refresh: forceRefresh,
          track: true,
        }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({ detail: 'Profiling failed' }));
        throw new Error(errJson.detail || `Server returned ${res.status}`);
      }

      const profile: CompanyProfile = await res.json();
      showToast(`Successfully profiled ${profile.legal_name}!`);
      onProfileComplete(profile);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setExecutionError(err.message);
      } else {
        setExecutionError('An unexpected error occurred during profiling');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Bulk Numbers Extraction
  const parseBulkNumbers = (text: string): { valid: string[]; invalid: string[] } => {
    const rawTokens = text.split(/[\r\n,;\s]+/).map((t) => t.trim()).filter(Boolean);
    const valid: string[] = [];
    const invalid: string[] = [];

    for (const t of rawTokens) {
      const res = validateNorwegianOrgNumber(t);
      if (res.isValid && !valid.includes(res.clean)) {
        valid.push(res.clean);
      } else if (!res.isValid) {
        invalid.push(t);
      }
    }
    return { valid, invalid };
  };

  const handleBulkSubmit = async () => {
    const { valid } = parseBulkNumbers(bulkInput);
    if (valid.length === 0) {
      showToast('No valid 9-digit Norwegian organization numbers found');
      return;
    }

    setIsSubmitting(true);
    setExecutionError(null);
    setCurrentStep(`Queuing batch indexing for ${valid.length} companies...`);

    try {
      const res = await fetch('/api/companies/bulk', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          org_numbers: valid,
          track: true,
          concurrency: 6,
        }),
      });

      if (!res.ok) {
        throw new Error('Failed to initiate bulk addition');
      }

      showToast(`Queued ${valid.length} companies for profiling! Check Batch Runs tab.`);
      setBulkInput('');
    } catch (err: any) {
      setExecutionError(err.message || 'Bulk submission failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  // File Upload Handler
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (evt) => {
      const content = evt.target?.result as string;
      if (content) {
        setBulkInput(content);
        setMode('bulk_text');
        showToast(`Loaded ${file.name}`);
      }
    };
    reader.readAsText(file);
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-in fade-in duration-300">
      <div>
        <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white flex items-center gap-3">
          <span>Add Company to Signalpost</span>
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 font-mono border border-indigo-200 dark:border-indigo-500/20">
            Live Provenance
          </span>
        </h2>
        <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 mt-1">
          Index, verify, and track any Norwegian enterprise from official Brønnøysundregistrene registers.
        </p>
      </div>

      {/* Input Mode Selector Tabs */}
      <div className="flex flex-wrap gap-2 p-1.5 rounded-2xl glass-panel max-w-2xl border border-slate-200 dark:border-slate-800">
        <button
          onClick={() => setMode('single')}
          className={`flex-1 py-2 px-3 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
            mode === 'single'
              ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
          }`}
        >
          Single 9-Digit Orgnr
        </button>
        <button
          onClick={() => setMode('search')}
          className={`flex-1 py-2 px-3 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
            mode === 'search'
              ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
          }`}
        >
          Search by Name
        </button>
        <button
          onClick={() => setMode('bulk_text')}
          className={`flex-1 py-2 px-3 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
            mode === 'bulk_text'
              ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
          }`}
        >
          Paste Multiple
        </button>
        <button
          onClick={() => setMode('upload')}
          className={`flex-1 py-2 px-3 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
            mode === 'upload'
              ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
          }`}
        >
          Upload File
        </button>
      </div>

      {/* MODE 1: SINGLE 9-DIGIT ORGNR */}
      {mode === 'single' && (
        <div className="p-6 rounded-2xl glass-panel space-y-6 border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider block">
              Enter Norwegian Organization Number
            </label>
            <div className="relative max-w-md">
              <input
                type="text"
                value={singleInput}
                onChange={(e) => setSingleInput(e.target.value)}
                placeholder="e.g. 923609016"
                className="w-full px-4 py-3 rounded-xl bg-white dark:bg-slate-900/90 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-white text-base font-mono placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 shadow-sm"
              />
              <div className="absolute right-3 top-1/2 -translate-y-1/2">
                {checksumResult.isValid ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-500 dark:text-emerald-400" />
                ) : singleInput ? (
                  <AlertCircle className="w-5 h-5 text-rose-500 dark:text-rose-400" />
                ) : null}
              </div>
            </div>
            {singleInput && !checksumResult.isValid && (
              <p className="text-xs text-rose-500 dark:text-rose-400 font-medium">{checksumResult.message}</p>
            )}
          </div>

          {/* Loading Preview */}
          {isPreviewLoading && (
            <div className="p-6 rounded-xl bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 text-center text-xs text-slate-600 dark:text-slate-400">
              <RefreshCw className="w-4 h-4 animate-spin mx-auto mb-2 text-indigo-500 dark:text-indigo-400" />
              <span>Checking official registry for {checksumResult.clean}...</span>
            </div>
          )}

          {/* Preview Error */}
          {previewError && (
            <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-rose-700 dark:text-rose-300 text-xs">
              {previewError}
            </div>
          )}

          {/* Live Preview Card */}
          {preview && (
            <div className="p-5 rounded-2xl bg-white dark:bg-slate-900/80 border border-indigo-200 dark:border-indigo-500/30 space-y-4 animate-in fade-in duration-200 shadow-md">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/20">
                      {preview.org_number}
                    </span>
                    <span className="text-xs font-mono text-slate-500 dark:text-slate-400">{preview.org_form}</span>
                  </div>
                  <h3 className="text-lg font-bold text-slate-900 dark:text-white mt-1">{preview.legal_name}</h3>
                  <p className="text-xs text-slate-600 dark:text-slate-400">
                    {preview.address || 'Address registered in Norway'} &bull;{' '}
                    {preview.municipality || 'Norge'}
                  </p>
                </div>

                <div>
                  {preview.status === 'ACTIVE' ? (
                    <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20">
                      Active
                    </span>
                  ) : (
                    <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 dark:bg-rose-500/10 dark:text-rose-400 border border-rose-200 dark:border-rose-500/20">
                      {preview.status}
                    </span>
                  )}
                </div>
              </div>

              {preview.is_already_profiled && (
                <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 text-xs text-amber-800 dark:text-amber-300 flex items-center justify-between">
                  <span>Already profiled in your local directory ({preview.facts_count} verified facts).</span>
                  <span className="text-[11px] text-amber-700 dark:text-amber-400 font-mono">
                    Last checked: {preview.last_checked_at ? new Date(preview.last_checked_at).toLocaleDateString() : 'recent'}
                  </span>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex items-center gap-3 pt-2">
                <button
                  onClick={() => handleConfirmSingle(preview.is_already_profiled)}
                  disabled={isSubmitting}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-bold text-white shadow-lg shadow-indigo-600/30 transition-all cursor-pointer disabled:opacity-50"
                >
                  {isSubmitting ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Processing Agent...</span>
                    </>
                  ) : preview.is_already_profiled ? (
                    <>
                      <RotateCcw className="w-4 h-4" />
                      <span>Refresh &amp; Re-verify Profile</span>
                    </>
                  ) : (
                    <>
                      <ShieldCheck className="w-4 h-4" />
                      <span>Confirm &amp; Profile Company</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* MODE 2: SEARCH BY COMPANY NAME */}
      {mode === 'search' && (
        <div className="p-6 rounded-2xl glass-panel space-y-6 border border-slate-200 dark:border-slate-800 shadow-sm">
          <form onSubmit={handleSearchSubmit} className="space-y-3">
            <label className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider block">
              Search Norwegian Company by Name
            </label>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="e.g. Equinor, DNB, Telenor, Kongsberg..."
                className="w-full px-4 py-2.5 rounded-xl bg-white dark:bg-slate-900/90 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-white text-sm placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 shadow-sm"
              />
              <button
                type="submit"
                disabled={isSearching}
                className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-bold text-white shadow-md shadow-indigo-600/30 transition-all cursor-pointer"
              >
                {isSearching ? 'Searching...' : 'Search'}
              </button>
            </div>
          </form>

          {/* Search Result Cards */}
          <div className="space-y-3">
            {searchResults.map((res) => (
              <div
                key={res.org_number}
                onClick={() => handleSelectSearchResult(res.org_number)}
                className="p-4 rounded-xl bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 hover:border-indigo-500/50 hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-all cursor-pointer flex items-center justify-between group shadow-sm"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-indigo-600 dark:text-indigo-400 font-semibold">
                      {res.org_number}
                    </span>
                    <span className="text-[11px] text-slate-500 font-mono">{res.org_form}</span>
                  </div>
                  <h4 className="text-sm font-bold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-300 transition-colors">
                    {res.legal_name}
                  </h4>
                  <p className="text-xs text-slate-600 dark:text-slate-400">{res.municipality || 'Norge'}</p>
                </div>

                <div className="flex items-center gap-2 text-xs font-semibold text-indigo-600 dark:text-indigo-400 group-hover:translate-x-1 transition-transform">
                  <span>Select</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* MODE 3: BULK NUMBERS TEXTAREA */}
      {mode === 'bulk_text' && (
        <div className="p-6 rounded-2xl glass-panel space-y-4 border border-slate-200 dark:border-slate-800 shadow-sm">
          <label className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider block">
            Paste Multiple 9-Digit Numbers (Line or Comma Separated)
          </label>
          <textarea
            rows={6}
            value={bulkInput}
            onChange={(e) => setBulkInput(e.target.value)}
            placeholder="923609016&#10;984851006&#10;976967631"
            className="w-full p-4 rounded-xl bg-white dark:bg-slate-900/90 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-white font-mono text-xs focus:outline-none focus:border-indigo-500 shadow-sm"
          />

          {bulkInput && (
            <div className="flex items-center gap-4 text-xs">
              <span className="text-emerald-600 dark:text-emerald-400 font-semibold">
                {parseBulkNumbers(bulkInput).valid.length} valid Mod-11 numbers
              </span>
              {parseBulkNumbers(bulkInput).invalid.length > 0 && (
                <span className="text-rose-600 dark:text-rose-400 font-medium">
                  {parseBulkNumbers(bulkInput).invalid.length} invalid numbers skipped
                </span>
              )}
            </div>
          )}

          <button
            onClick={handleBulkSubmit}
            disabled={isSubmitting || parseBulkNumbers(bulkInput).valid.length === 0}
            className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-bold text-white shadow-md shadow-indigo-600/30 transition-all cursor-pointer disabled:opacity-40"
          >
            {isSubmitting ? 'Queuing Batch...' : 'Queue Bulk Profiling'}
          </button>
        </div>
      )}

      {/* MODE 4: FILE UPLOAD */}
      {mode === 'upload' && (
        <div className="p-8 rounded-2xl glass-panel text-center border-2 border-dashed border-slate-300 dark:border-slate-700 hover:border-indigo-500/50 transition-all space-y-4">
          <Upload className="w-8 h-8 text-indigo-600 dark:text-indigo-400 mx-auto" />
          <div>
            <h4 className="text-sm font-bold text-slate-900 dark:text-white">Upload Organization List (.TXT or .CSV)</h4>
            <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
              Select any text or CSV file containing 9-digit Norwegian organization numbers.
            </p>
          </div>
          <label className="inline-block px-5 py-2.5 rounded-xl bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 cursor-pointer transition-colors shadow-sm">
            <span>Browse File</span>
            <input
              type="file"
              accept=".txt,.csv"
              onChange={handleFileUpload}
              className="hidden"
            />
          </label>
        </div>
      )}

      {/* Live Processing Step Indicator */}
      {isSubmitting && (
        <div className="p-4 rounded-2xl bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/30 flex items-center gap-3 text-indigo-700 dark:text-indigo-300 text-xs font-medium animate-pulse">
          <RefreshCw className="w-4 h-4 animate-spin text-indigo-600 dark:text-indigo-400" />
          <span>{currentStep}</span>
        </div>
      )}

      {/* Execution Error Banner */}
      {executionError && (
        <div className="p-4 rounded-2xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/30 text-rose-700 dark:text-rose-300 text-xs flex items-center justify-between">
          <span>{executionError}</span>
          <button
            onClick={() => handleConfirmSingle(true)}
            className="px-3 py-1 rounded bg-rose-100 dark:bg-rose-500/20 hover:bg-rose-200 dark:hover:bg-rose-500/30 text-rose-800 dark:text-rose-200 text-xs font-bold cursor-pointer"
          >
            Retry
          </button>
        </div>
      )}
    </div>
  );
};
