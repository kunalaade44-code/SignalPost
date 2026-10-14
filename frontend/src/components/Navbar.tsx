import React from 'react';
import {
  Compass,
  Search,
  Building2,
  Layers,
  BarChart3,
  Sun,
  Moon,
  Settings,
} from 'lucide-react';

export type NavTab = 'search' | 'companies' | 'add' | 'batch' | 'quality' | 'system';

interface NavbarProps {
  activeTab: NavTab;
  setActiveTab: (tab: NavTab) => void;
  isDarkMode: boolean;
  onToggleTheme: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  isDarkMode,
  onToggleTheme,
}) => {
  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 dark:border-slate-800/80 bg-white/90 dark:bg-[#0b0f19]/90 backdrop-blur-md transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Product Logo / Name */}
          <div
            className="flex items-center gap-3 cursor-pointer group"
            onClick={() => setActiveTab('search')}
          >
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-emerald-400 flex items-center justify-center shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
              <Compass className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="text-lg font-bold tracking-tight text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-300 transition-colors">
                Signalpost
              </span>
              <span className="hidden sm:inline-block ml-2 text-[11px] font-medium text-slate-500 dark:text-slate-400">
                Company Intelligence
              </span>
            </div>
          </div>

          {/* Navigation Pages */}
          <nav className="hidden md:flex items-center gap-1">
            <button
              onClick={() => setActiveTab('search')}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                activeTab === 'search'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/50'
              }`}
            >
              <Search className="w-3.5 h-3.5" />
              <span>Search</span>
            </button>

            <button
              onClick={() => setActiveTab('companies')}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                activeTab === 'companies'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/50'
              }`}
            >
              <Building2 className="w-3.5 h-3.5" />
              <span>Companies</span>
            </button>

            <button
              onClick={() => setActiveTab('batch')}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                activeTab === 'batch'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/50'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Batch Runs</span>
            </button>

            <button
              onClick={() => setActiveTab('quality')}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                activeTab === 'quality'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/50'
              }`}
            >
              <BarChart3 className="w-3.5 h-3.5" />
              <span>Quality Report</span>
            </button>
          </nav>

          {/* Right Action Cluster */}
          <div className="flex items-center gap-2">
            {/* Dark / Light Toggle */}
            <button
              onClick={onToggleTheme}
              aria-label="Toggle dark/light mode"
              className="p-2 rounded-xl text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800/60 transition-colors cursor-pointer"
            >
              {isDarkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>

            {/* System / Settings Tab */}
            <button
              onClick={() => setActiveTab('system')}
              aria-label="System Settings"
              className={`p-2 rounded-xl transition-colors cursor-pointer ${
                activeTab === 'system'
                  ? 'bg-slate-100 dark:bg-slate-800 text-indigo-600 dark:text-indigo-400'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800/60'
              }`}
            >
              <Settings className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Navigation Row */}
      <div className="md:hidden flex items-center justify-around py-2 border-t border-slate-200 dark:border-slate-800/60 bg-white/90 dark:bg-slate-950/60 text-xs">
        <button
          onClick={() => setActiveTab('search')}
          className={`px-3 py-1.5 rounded-lg ${activeTab === 'search' ? 'text-indigo-600 dark:text-indigo-400 font-bold' : 'text-slate-600 dark:text-slate-400'}`}
        >
          Search
        </button>
        <button
          onClick={() => setActiveTab('companies')}
          className={`px-3 py-1.5 rounded-lg ${activeTab === 'companies' ? 'text-indigo-600 dark:text-indigo-400 font-bold' : 'text-slate-600 dark:text-slate-400'}`}
        >
          Companies
        </button>
        <button
          onClick={() => setActiveTab('batch')}
          className={`px-3 py-1.5 rounded-lg ${activeTab === 'batch' ? 'text-indigo-600 dark:text-indigo-400 font-bold' : 'text-slate-600 dark:text-slate-400'}`}
        >
          Batch
        </button>
        <button
          onClick={() => setActiveTab('quality')}
          className={`px-3 py-1.5 rounded-lg ${activeTab === 'quality' ? 'text-indigo-600 dark:text-indigo-400 font-bold' : 'text-slate-600 dark:text-slate-400'}`}
        >
          Quality
        </button>
      </div>
    </header>
  );
};
