import { useState, useEffect, useCallback } from 'react';
import {
  Building2,
  ShieldCheck,
  AlertCircle,
  Database,
  ArrowRight,
  Sparkles,
  Layers,
  FileCheck2,
  CheckCircle,
} from 'lucide-react';
import { Navbar, type NavTab } from './components/Navbar';
import { SearchHero } from './components/SearchHero';
import { ProfileView } from './components/ProfileView';
import { CompaniesView } from './components/CompaniesView';
import { AddCompanyView } from './components/AddCompanyView';
import { EvidenceDrawer } from './components/EvidenceDrawer';
import { BatchView } from './components/BatchView';
import { QualityReportView } from './components/QualityReportView';
import { SettingsView } from './components/SettingsView';
import type { CompanyProfile, Fact, SystemStats } from './types';

export function App() {
  const [activeTab, setActiveTab] = useState<NavTab>('search');
  const [selectedProfile, setSelectedProfile] = useState<CompanyProfile | null>(null);
  const [evidenceFact, setEvidenceFact] = useState<Fact | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Theme state with localStorage persistence
  const [isDarkMode, setIsDarkMode] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('signalpost_theme');
      if (saved) return saved === 'dark';
      return document.documentElement.classList.contains('dark');
    }
    return true;
  });

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('signalpost_theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('signalpost_theme', 'light');
    }
  }, [isDarkMode]);

  // Toast notification state
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = useCallback((msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage((current) => (current === msg ? null : current));
    }, 3500);
  }, []);

  // Health and System Stats
  const [isHealthy, setIsHealthy] = useState<boolean>(true);
  const [supabaseConfigured, setSupabaseConfigured] = useState<boolean>(false);
  const [stats, setStats] = useState<SystemStats | null>(null);

  const fetchHealthAndStats = useCallback(async () => {
    try {
      const healthRes = await fetch('/api/health');
      if (healthRes.ok) {
        const hData = await healthRes.json();
        setIsHealthy(hData.status === 'healthy');
        setSupabaseConfigured(Boolean(hData.supabase_configured));
      }

      const statsRes = await fetch('/api/stats');
      if (statsRes.ok) {
        const sData = await statsRes.json();
        setStats(sData);
      }
    } catch {
      setIsHealthy(false);
    }
  }, []);

  useEffect(() => {
    fetchHealthAndStats();
    const interval = setInterval(fetchHealthAndStats, 30000);
    return () => clearInterval(interval);
  }, [fetchHealthAndStats]);

  const handleSearch = useCallback(
    async (orgnr: string, force = false) => {
      setIsLoading(true);
      setError(null);
      setActiveTab('search');

      try {
        const res = await fetch(`/api/company/${orgnr}?force=${force}`);
        if (!res.ok) {
          const errJson = await res.json().catch(() => ({ detail: 'Failed to profile company' }));
          throw new Error(errJson.detail || `Error profiling company (${res.status})`);
        }
        const data: CompanyProfile = await res.json();
        setSelectedProfile(data);
        fetchHealthAndStats();

        // Update URL query parameter cleanly without reloading
        const newUrl = `${window.location.pathname}?orgnr=${orgnr}`;
        window.history.pushState({ path: newUrl }, '', newUrl);
      } catch (err: unknown) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError('An unexpected error occurred while searching');
        }
      } finally {
        setIsLoading(false);
      }
    },
    [fetchHealthAndStats]
  );

  // Check URL query on mount (e.g. ?orgnr=923609016)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const orgParam = params.get('orgnr');
    if (orgParam && /^\d{9}$/.test(orgParam)) {
      handleSearch(orgParam);
    }
  }, [handleSearch]);

  const toggleTheme = () => {
    setIsDarkMode((prev) => !prev);
  };

  return (
    <div className={`min-h-screen ${isDarkMode ? 'dark bg-[#0b0f19] text-slate-100' : 'bg-slate-50 text-slate-900'} flex flex-col font-sans transition-colors duration-200`}>
      {/* SaaS Top Navigation */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isDarkMode={isDarkMode}
        onToggleTheme={toggleTheme}
      />

      {/* Main View Area */}
      <main className="flex-1">
        {/* 1. SEARCH & LANDING PAGE */}
        {activeTab === 'search' && (
          <div>
            <SearchHero onSearch={handleSearch} isLoading={isLoading} />

            {/* Error Banner */}
            {error && (
              <div className="max-w-4xl mx-auto px-4 mb-6">
                <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-3 text-rose-600 dark:text-rose-300">
                  <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                  <div className="text-sm">
                    <p className="font-semibold">Lookup Failed</p>
                    <p className="text-rose-800 dark:text-rose-200/80">{error}</p>
                  </div>
                </div>
              </div>
            )}

            {/* If Company is Selected, display ProfileView */}
            {selectedProfile ? (
              <div className="space-y-4">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-4">
                  <button
                    onClick={() => {
                      setSelectedProfile(null);
                      const cleanUrl = window.location.pathname;
                      window.history.pushState({}, '', cleanUrl);
                    }}
                    className="inline-flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-white font-medium cursor-pointer"
                  >
                    <span>&larr; Back to Directory Search</span>
                  </button>
                </div>

                <ProfileView
                  profile={selectedProfile}
                  onSelectFact={(fact) => setEvidenceFact(fact)}
                  onRefreshData={(orgnr) => handleSearch(orgnr, true)}
                  showToast={showToast}
                />
              </div>
            ) : (
              /* Overview Stats & Showcases when no profile is active */
              <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pb-16 space-y-10">
                {/* Real-time Telemetry Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-5 rounded-2xl glass-panel space-y-1 border border-slate-200 dark:border-slate-800 shadow-sm">
                    <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
                      <span className="text-xs font-semibold uppercase tracking-wider">Profiles Stored</span>
                      <Building2 className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                    </div>
                    <div className="text-2xl font-bold text-slate-900 dark:text-white font-mono">
                      {stats?.database?.total_profiles ?? 0}
                    </div>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400">Verified Norwegian entities</p>
                  </div>

                  <div className="p-5 rounded-2xl glass-panel space-y-1 border border-slate-200 dark:border-slate-800 shadow-sm">
                    <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
                      <span className="text-xs font-semibold uppercase tracking-wider">Verified Facts</span>
                      <FileCheck2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                    </div>
                    <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 font-mono">
                      {stats?.database?.total_verified_facts ?? 0}
                    </div>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400">With source URI &amp; timestamps</p>
                  </div>

                  <div className="p-5 rounded-2xl glass-panel space-y-1 border border-slate-200 dark:border-slate-800 shadow-sm">
                    <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
                      <span className="text-xs font-semibold uppercase tracking-wider">Audit Revisions</span>
                      <Layers className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                    </div>
                    <div className="text-2xl font-bold text-indigo-600 dark:text-indigo-300 font-mono">
                      {stats?.database?.total_audit_events ?? 0}
                    </div>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400">SHA-256 diff hash trail</p>
                  </div>

                  <div className="p-5 rounded-2xl glass-panel space-y-1 border border-slate-200 dark:border-slate-800 shadow-sm">
                    <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
                      <span className="text-xs font-semibold uppercase tracking-wider">Fabrication Policy</span>
                      <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                    </div>
                    <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 font-mono">
                      0%
                    </div>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400">Verbatim public registry data</p>
                  </div>
                </div>

                {/* Featured Sample Companies */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                        <Sparkles className="w-4 h-4 text-amber-500 dark:text-amber-400" />
                        <span>Featured Norwegian Enterprises</span>
                      </h3>
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        Select any registered organisation to inspect facts, official roles, and verified financial records.
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {[
                      {
                        name: 'Equinor ASA',
                        orgnr: '923609016',
                        form: 'ASA',
                        sector: 'Energy & Offshore',
                        location: 'Stavanger',
                      },
                      {
                        name: 'DNB Bank ASA',
                        orgnr: '984851006',
                        form: 'ASA',
                        sector: 'Financial Banking',
                        location: 'Oslo',
                      },
                      {
                        name: 'Telenor ASA',
                        orgnr: '976967631',
                        form: 'ASA',
                        sector: 'Telecommunications',
                        location: 'Fornebu',
                      },
                      {
                        name: 'Norsk Hydro ASA',
                        orgnr: '917088713',
                        form: 'ASA',
                        sector: 'Aluminium & Energy',
                        location: 'Oslo',
                      },
                      {
                        name: 'Schibsted ASA',
                        orgnr: '938708606',
                        form: 'ASA',
                        sector: 'Publishing & Media',
                        location: 'Oslo',
                      },
                      {
                        name: 'Yara International ASA',
                        orgnr: '986228608',
                        form: 'ASA',
                        sector: 'Chemicals & Ag',
                        location: 'Oslo',
                      },
                    ].map((comp) => (
                      <div
                        key={comp.orgnr}
                        onClick={() => handleSearch(comp.orgnr)}
                        className="p-5 rounded-2xl glass-panel hover:border-indigo-400 dark:hover:border-indigo-500/50 hover:bg-slate-50 dark:hover:bg-slate-800/40 border border-slate-200 dark:border-slate-800 shadow-sm transition-all cursor-pointer group flex flex-col justify-between"
                      >
                        <div className="space-y-2">
                          <div className="flex items-start justify-between">
                            <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/20">
                              {comp.orgnr}
                            </span>
                            <span className="text-[11px] text-slate-500 dark:text-slate-400 font-mono">
                              {comp.form}
                            </span>
                          </div>
                          <div>
                            <h4 className="text-sm font-bold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-300 transition-colors">
                              {comp.name}
                            </h4>
                            <p className="text-xs text-slate-500 dark:text-slate-400">{comp.sector} &bull; {comp.location}</p>
                          </div>
                        </div>

                        <div className="pt-4 flex items-center justify-between text-xs text-indigo-600 dark:text-indigo-400 font-semibold group-hover:translate-x-0.5 transition-transform">
                          <span>Inspect Verified Profile</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Trust & Provenance Card */}
                <div className="p-6 rounded-2xl glass-panel border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
                  <div className="flex items-start gap-4">
                    <div className="p-3 rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-500/20">
                      <Database className="w-6 h-6" />
                    </div>
                    <div className="space-y-1">
                      <h4 className="text-sm font-bold text-slate-900 dark:text-white">
                        Authoritative Public Registry Integration
                      </h4>
                      <p className="text-xs text-slate-600 dark:text-slate-400 max-w-2xl leading-relaxed">
                        Signalpost operates directly against the Brønnøysundregistrene Open Data APIs (Enhetsregisteret and Regnskapsregisteret) under Norwegian Licence for Open Government Data (NLOD 2.0). Every single fact includes an explicit source URI, timestamp, and verification evidence.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* 2. COMPANIES DIRECTORY VIEW */}
        {activeTab === 'companies' && (
          <CompaniesView
            onSelectOrgnr={(orgnr) => handleSearch(orgnr)}
            onNavigateAdd={() => setActiveTab('add')}
            showToast={showToast}
          />
        )}

        {/* 3. ADD COMPANY VIEW */}
        {activeTab === 'add' && (
          <AddCompanyView
            onProfileComplete={(profile) => {
              setSelectedProfile(profile);
              setActiveTab('search');
            }}
            showToast={showToast}
          />
        )}

        {/* 4. BATCH VIEW */}
        {activeTab === 'batch' && (
          <BatchView
            onSelectOrgnr={(orgnr) => handleSearch(orgnr)}
          />
        )}

        {/* 5. QUALITY REPORT VIEW */}
        {activeTab === 'quality' && <QualityReportView />}

        {/* 6. SETTINGS & SYSTEM VIEW */}
        {activeTab === 'system' && (
          <SettingsView
            stats={stats}
            isHealthy={isHealthy}
            supabaseConfigured={supabaseConfigured}
          />
        )}
      </main>

      {/* Slide-out Evidence & Provenance Drawer */}
      <EvidenceDrawer
        fact={evidenceFact}
        onClose={() => setEvidenceFact(null)}
      />

      {/* Toast Notification Banner */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 animate-in slide-in-from-bottom-3 duration-300">
          <div className="px-4 py-3 rounded-xl bg-indigo-600 text-white text-xs font-semibold shadow-2xl flex items-center gap-2 border border-indigo-400/40">
            <CheckCircle className="w-4 h-4 text-emerald-300" />
            <span>{toastMessage}</span>
          </div>
        </div>
      )}

      {/* SaaS Clean Footer */}
      <footer className="border-t border-slate-200 dark:border-slate-800/80 bg-white/60 dark:bg-slate-950/40 py-6 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500 dark:text-slate-400">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-700 dark:text-slate-300">Signalpost</span>
            <span>&bull;</span>
            <span>Norwegian Company Intelligence Engine</span>
          </div>

          <div className="flex items-center gap-4">
            <span>Data: Brønnøysundregistrene (NLOD 2.0)</span>
            <span>&bull;</span>
            <button
              onClick={() => setActiveTab('system')}
              className="text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white underline cursor-pointer"
            >
              System &amp; Settings
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
