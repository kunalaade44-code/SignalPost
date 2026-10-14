import React, { useState, useEffect, useCallback } from 'react';
import {
  Search,
  Download,
  Building2,
  CheckCircle,
  AlertOctagon,
  AlertTriangle,
  ArrowRight,
  Star,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  FileSpreadsheet,
  ArrowUpDown,
} from 'lucide-react';

interface CompanyListItem {
  org_number: string;
  legal_name: string;
  status: string;
  org_form: string;
  municipality?: string | null;
  employees?: number | null;
  facts_count: number;
  is_tracked: boolean;
  last_checked_at: string;
}

interface CompaniesViewProps {
  onSelectOrgnr: (orgnr: string) => void;
  onNavigateAdd: () => void;
  showToast: (msg: string) => void;
}

export const CompaniesView: React.FC<CompaniesViewProps> = ({
  onSelectOrgnr,
  onNavigateAdd,
  showToast,
}) => {
  const [items, setItems] = useState<CompanyListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [municipalityFilter, setMunicipalityFilter] = useState('');
  const [trackedOnly, setTrackedOnly] = useState(false);
  const [sortBy, setSortBy] = useState('last_checked_at');
  const [sortOrder, setSortOrder] = useState('desc');

  const fetchCompanies = useCallback(async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        size: '15',
        sort_by: sortBy,
        sort_order: sortOrder,
      });
      if (search.trim()) params.set('search', search.trim());
      if (statusFilter) params.set('status', statusFilter);
      if (municipalityFilter.trim()) params.set('municipality', municipalityFilter.trim());
      if (trackedOnly) params.set('tracked_only', 'true');

      const res = await fetch(`/api/companies?${params.toString()}`);
      if (res.ok) {
        const data = await res.json();
        setItems(data.items || []);
        setTotal(data.total || 0);
        setTotalPages(data.pages || 1);
      }
    } catch {
      showToast('Failed to load companies directory');
    } finally {
      setIsLoading(false);
    }
  }, [page, sortBy, sortOrder, search, statusFilter, municipalityFilter, trackedOnly, showToast]);

  useEffect(() => {
    fetchCompanies();
  }, [fetchCompanies]);

  const handleToggleTrack = async (e: React.MouseEvent, orgnr: string) => {
    e.stopPropagation();
    try {
      const res = await fetch(`/api/companies/${orgnr}/track`, { method: 'PATCH' });
      if (res.ok) {
        const data = await res.json();
        setItems((prev) =>
          prev.map((item) =>
            item.org_number === orgnr ? { ...item, is_tracked: data.is_tracked } : item
          )
        );
        showToast(
          data.is_tracked
            ? `Added ${orgnr} to tracked watchlist`
            : `Removed ${orgnr} from watchlist`
        );
      }
    } catch {
      showToast('Failed to update watchlist status');
    }
  };

  const handleExportCSV = () => {
    if (items.length === 0) return;
    const headers = [
      'org_number',
      'legal_name',
      'status',
      'org_form',
      'municipality',
      'employees',
      'facts_count',
      'is_tracked',
      'last_checked_at',
    ];
    const rows = items.map((i) =>
      [
        i.org_number,
        `"${(i.legal_name || '').replace(/"/g, '""')}"`,
        i.status,
        i.org_form,
        `"${i.municipality || ''}"`,
        i.employees ?? '',
        i.facts_count,
        i.is_tracked ? 'YES' : 'NO',
        i.last_checked_at,
      ].join(',')
    );

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `signalpost_companies_page_${page}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    showToast('Exported CSV successfully');
  };

  const handleExportJSON = () => {
    if (items.length === 0) return;
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(items, null, 2));
    const link = document.createElement('a');
    link.setAttribute('href', dataStr);
    link.setAttribute('download', `signalpost_companies_page_${page}.json`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    showToast('Exported JSON successfully');
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6 animate-in fade-in duration-300">
      {/* Top Heading & Action Row */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white flex items-center gap-3">
            <span>Companies Directory</span>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300 font-mono border border-indigo-200 dark:border-indigo-500/20">
              {total.toLocaleString()} profiled
            </span>
          </h2>
          <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 mt-1">
            Browse, filter, and monitor verified Norwegian organizations in your local intelligence store.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleExportCSV}
            disabled={items.length === 0}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 transition-colors disabled:opacity-40 cursor-pointer shadow-sm"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
            <span>CSV</span>
          </button>
          <button
            onClick={handleExportJSON}
            disabled={items.length === 0}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 transition-colors disabled:opacity-40 cursor-pointer shadow-sm"
          >
            <Download className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
            <span>JSON</span>
          </button>
          <button
            onClick={onNavigateAdd}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white shadow-md shadow-indigo-600/20 transition-all cursor-pointer"
          >
            <span>+ Add Company</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-2xl glass-panel space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {/* Text Search */}
          <div className="relative lg:col-span-2">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder="Search by company name or 9-digit orgnr..."
              className="w-full pl-9 pr-3 py-2 rounded-xl bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white text-xs placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>

          {/* Status Filter */}
          <div className="relative">
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="w-full px-3 py-2 rounded-xl bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-300 text-xs focus:outline-none focus:border-indigo-500"
            >
              <option value="">All Statuses</option>
              <option value="ACTIVE">Active</option>
              <option value="BANKRUPT">Bankrupt</option>
              <option value="IN_LIQUIDATION">In Liquidation</option>
              <option value="DISSOLVED">Dissolved</option>
            </select>
          </div>

          {/* Municipality Filter */}
          <div>
            <input
              type="text"
              value={municipalityFilter}
              onChange={(e) => {
                setMunicipalityFilter(e.target.value);
                setPage(1);
              }}
              placeholder="Filter municipality..."
              className="w-full px-3 py-2 rounded-xl bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white text-xs placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>

          {/* Sort By & Order */}
          <div className="flex items-center gap-1.5">
            <select
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value);
                setPage(1);
              }}
              className="w-full px-3 py-2 rounded-xl bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-300 text-xs focus:outline-none focus:border-indigo-500"
            >
              <option value="last_checked_at">Sort: Last Inspected</option>
              <option value="legal_name">Sort: Company Name</option>
              <option value="employees">Sort: Employees</option>
              <option value="facts_count">Sort: Verified Facts</option>
            </select>
            <button
              type="button"
              onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
              title={`Sorting ${sortOrder.toUpperCase()}`}
              className="p-2 rounded-xl bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white cursor-pointer shadow-sm"
            >
              <ArrowUpDown className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Watchlist Toggle Pill */}
        <div className="flex items-center justify-between text-xs pt-1">
          <button
            onClick={() => {
              setTrackedOnly(!trackedOnly);
              setPage(1);
            }}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg border text-xs font-medium transition-all cursor-pointer ${
              trackedOnly
                ? 'bg-amber-500/20 text-amber-600 dark:text-amber-300 border-amber-500/30'
                : 'bg-white dark:bg-slate-900/60 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-800 hover:text-slate-900 dark:hover:text-slate-200 shadow-sm'
            }`}
          >
            <Star className={`w-3.5 h-3.5 ${trackedOnly ? 'fill-amber-400 text-amber-500 dark:text-amber-400' : ''}`} />
            <span>Watchlist Only</span>
          </button>

          {(search || statusFilter || municipalityFilter || trackedOnly) && (
            <button
              onClick={() => {
                setSearch('');
                setStatusFilter('');
                setMunicipalityFilter('');
                setTrackedOnly(false);
                setPage(1);
              }}
              className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 font-medium cursor-pointer"
            >
              Clear all filters
            </button>
          )}
        </div>
      </div>

      {/* Directory Table */}
      <div className="glass-panel rounded-2xl overflow-hidden border border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-100 dark:bg-slate-900/80 text-slate-700 dark:text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-200 dark:border-slate-800">
              <tr>
                <th className="py-3 px-4 w-10"></th>
                <th className="py-3 px-4">Org Number</th>
                <th className="py-3 px-4">Company Name</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Municipality</th>
                <th className="py-3 px-4">Employees</th>
                <th className="py-3 px-4">Verified Facts</th>
                <th className="py-3 px-4">Last Inspected</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800/60 text-slate-700 dark:text-slate-300 font-sans">
              {isLoading ? (
                <tr>
                  <td colSpan={9} className="py-16 text-center text-slate-500">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-indigo-500 dark:text-indigo-400" />
                    <span>Loading directory...</span>
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-16 text-center space-y-3">
                    <Building2 className="w-8 h-8 mx-auto text-slate-400 dark:text-slate-600" />
                    <p className="text-slate-600 dark:text-slate-400 text-sm font-medium">No companies match your query.</p>
                    <button
                      onClick={onNavigateAdd}
                      className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold cursor-pointer shadow-sm"
                    >
                      + Add Company Now
                    </button>
                  </td>
                </tr>
              ) : (
                items.map((c) => (
                  <tr
                    key={c.org_number}
                    onClick={() => onSelectOrgnr(c.org_number)}
                    className="hover:bg-slate-100/70 dark:hover:bg-slate-800/40 transition-colors cursor-pointer group"
                  >
                    {/* Star Watchlist */}
                    <td className="py-3.5 px-4" onClick={(e) => handleToggleTrack(e, c.org_number)}>
                      <button className="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700/60 transition-colors cursor-pointer">
                        <Star
                          className={`w-4 h-4 ${
                            c.is_tracked
                              ? 'fill-amber-400 text-amber-500 dark:text-amber-400'
                              : 'text-slate-300 dark:text-slate-600 hover:text-slate-500 dark:hover:text-slate-400'
                          }`}
                        />
                      </button>
                    </td>

                    {/* Org Number */}
                    <td className="py-3.5 px-4 font-mono font-semibold text-indigo-600 dark:text-indigo-300">
                      {c.org_number}
                    </td>

                    {/* Legal Name */}
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-300 transition-colors flex items-center gap-1.5">
                        <span>{c.legal_name}</span>
                        {c.org_form && (
                          <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-mono border border-slate-200 dark:border-slate-700">
                            {c.org_form}
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Status */}
                    <td className="py-3.5 px-4">
                      {c.status === 'ACTIVE' ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20">
                          <CheckCircle className="w-3 h-3" />
                          <span>Active</span>
                        </span>
                      ) : c.status === 'BANKRUPT' ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-50 text-rose-700 dark:bg-rose-500/10 dark:text-rose-400 border border-rose-200 dark:border-rose-500/20">
                          <AlertOctagon className="w-3 h-3" />
                          <span>Bankrupt</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400 border border-amber-200 dark:border-amber-500/20">
                          <AlertTriangle className="w-3 h-3" />
                          <span>{c.status}</span>
                        </span>
                      )}
                    </td>

                    {/* Municipality */}
                    <td className="py-3.5 px-4 text-slate-600 dark:text-slate-400">
                      {c.municipality || '—'}
                    </td>

                    {/* Employees */}
                    <td className="py-3.5 px-4 font-mono text-slate-700 dark:text-slate-300">
                      {c.employees !== null && c.employees !== undefined
                        ? c.employees.toLocaleString()
                        : '—'}
                    </td>

                    {/* Facts Count */}
                    <td className="py-3.5 px-4 font-mono">
                      <span className="px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/20">
                        {c.facts_count} facts
                      </span>
                    </td>

                    {/* Last Checked */}
                    <td className="py-3.5 px-4 text-slate-500 dark:text-slate-400 font-mono text-[11px]">
                      {new Date(c.last_checked_at).toLocaleDateString()}
                    </td>

                    {/* View Action */}
                    <td className="py-3.5 px-4 text-right">
                      <span className="inline-flex items-center gap-1 text-indigo-600 dark:text-indigo-400 font-semibold group-hover:translate-x-0.5 transition-transform">
                        <span>Profile</span>
                        <ArrowRight className="w-3 h-3" />
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        <div className="p-4 bg-slate-50 dark:bg-slate-900/60 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs text-slate-600 dark:text-slate-400">
          <div>
            Showing Page <span className="font-bold text-slate-900 dark:text-white">{page}</span> of{' '}
            <span className="font-bold text-slate-900 dark:text-white">{totalPages}</span> ({total.toLocaleString()} total companies)
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-700 dark:text-white disabled:opacity-40 disabled:pointer-events-none cursor-pointer shadow-sm"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-700 dark:text-white disabled:opacity-40 disabled:pointer-events-none cursor-pointer shadow-sm"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
