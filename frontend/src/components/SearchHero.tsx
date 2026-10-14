import React, { useState } from 'react';
import { Search, CheckCircle2, AlertCircle, RefreshCw, Sparkles, Building2 } from 'lucide-react';
import { validateNorwegianOrgNumber } from '../utils/checksum';

interface SearchHeroProps {
  onSearch: (orgnr: string, force: boolean) => void;
  isLoading: boolean;
}

const SAMPLE_COMPANIES = [
  { name: 'Equinor ASA', orgnr: '923609016', sector: 'Energy' },
  { name: 'DNB Bank ASA', orgnr: '984851006', sector: 'Finance' },
  { name: 'Telenor ASA', orgnr: '976967631', sector: 'Telecom' },
  { name: 'Norsk Hydro ASA', orgnr: '917088713', sector: 'Aluminium' },
  { name: 'Schibsted ASA', orgnr: '938708606', sector: 'Media' },
];

export const SearchHero: React.FC<SearchHeroProps> = ({ onSearch, isLoading }) => {
  const [inputValue, setInputValue] = useState('');
  const [forceRefresh, setForceRefresh] = useState(false);

  const checksumResult = validateNorwegianOrgNumber(inputValue);

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (checksumResult.isValid) {
      onSearch(checksumResult.clean, forceRefresh);
    }
  };

  const handleSelectSample = (orgnr: string) => {
    setInputValue(orgnr);
    onSearch(orgnr, forceRefresh);
  };

  return (
    <div className="relative py-12 px-4 sm:px-6 lg:px-8 text-center max-w-4xl mx-auto">
      {/* Decorative gradient glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Title */}
      <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/20 text-xs font-semibold mb-6">
        <Sparkles className="w-3.5 h-3.5 text-amber-500 dark:text-amber-400" />
        <span>Verified Norwegian Company Intelligence</span>
      </div>

      <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-slate-900 dark:text-white mb-4">
        Verify Norwegian Companies <br />
        <span className="bg-gradient-to-r from-indigo-600 via-indigo-500 to-emerald-500 dark:from-indigo-400 dark:via-indigo-200 dark:to-emerald-400 bg-clip-text text-transparent">
          With Zero Hallucination & Evidence
        </span>
      </h1>

      <p className="text-base sm:text-lg text-slate-600 dark:text-slate-300 max-w-2xl mx-auto mb-8">
        Input any 9-digit Norwegian organization number. Signalpost searches official registries, verifies
        financial statements verbatim, crawls official domains, and binds facts with cryptographic provenance.
      </p>

      {/* Search Input Box */}
      <form onSubmit={handleFormSubmit} className="max-w-2xl mx-auto mb-4">
        <div className="relative flex items-center rounded-2xl glass-panel p-2">
          <div className="pl-3 pr-2 text-slate-400 dark:text-slate-500">
            <Building2 className="w-5 h-5" />
          </div>

          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter 9-digit org number (e.g. 923 609 016)"
            className="w-full bg-transparent text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 text-base sm:text-lg font-medium focus:outline-none px-2 py-2"
            maxLength={13}
          />

          <button
            type="submit"
            disabled={!checksumResult.isValid || isLoading}
            className={`flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-sm transition-all shadow-md ${
              checksumResult.isValid && !isLoading
                ? 'bg-gradient-to-r from-indigo-600 to-emerald-500 hover:from-indigo-500 hover:to-emerald-400 text-white cursor-pointer shadow-indigo-500/25'
                : 'bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-500 cursor-not-allowed border border-slate-200 dark:border-slate-700/50'
            }`}
          >
            {isLoading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Profiling...</span>
              </>
            ) : (
              <>
                <Search className="w-4 h-4" />
                <span>Verify Profile</span>
              </>
            )}
          </button>
        </div>

        {/* Real-time checksum indicator below input */}
        <div className="flex items-center justify-between px-2 mt-2 text-xs">
          <div className="flex items-center gap-1.5">
            {inputValue.trim().length > 0 && (
              <>
                {checksumResult.isValid ? (
                  <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>{checksumResult.message}</span>
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-amber-600 dark:text-amber-400">
                    <AlertCircle className="w-3.5 h-3.5" />
                    <span>{checksumResult.message}</span>
                  </span>
                )}
              </>
            )}
          </div>

          <label className="flex items-center gap-2 text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={forceRefresh}
              onChange={(e) => setForceRefresh(e.target.checked)}
              className="rounded bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-700 text-indigo-600 focus:ring-0"
            />
            <span>Bypass Cache (Force Live Crawl)</span>
          </label>
        </div>
      </form>

      {/* Sample Quick Chips */}
      <div className="flex flex-wrap items-center justify-center gap-2 pt-2">
        <span className="text-xs text-slate-500 dark:text-slate-400 mr-1 font-medium">Quick samples:</span>
        {SAMPLE_COMPANIES.map((company) => (
          <button
            key={company.orgnr}
            type="button"
            onClick={() => handleSelectSample(company.orgnr)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white dark:bg-slate-800/60 hover:bg-slate-50 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700/60 hover:border-indigo-400 dark:hover:border-indigo-500/50 text-xs font-medium text-slate-700 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-white transition-all cursor-pointer shadow-sm"
          >
            <span>{company.name}</span>
            <span className="text-[10px] px-1.5 py-0.2 rounded bg-indigo-50 text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-300 font-mono">
              {company.orgnr}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
};
