import React, { useState } from 'react';
import {
  Building2,
  Calendar,
  MapPin,
  Users,
  CheckCircle,
  AlertOctagon,
  ExternalLink,
  ShieldCheck,
  Download,
  DollarSign,
  Briefcase,
  Globe,
  Mail,
  Phone,
  AlertTriangle,
  History,
  Copy,
  RefreshCw,
  Clock,
  Star,
} from 'lucide-react';
import type { CompanyProfile, Fact } from '../types';
import { FinancialChart } from './FinancialChart';

interface ProfileViewProps {
  profile: CompanyProfile;
  onSelectFact: (fact: Fact) => void;
  onRefreshData: (orgnr: string) => void;
  showToast: (msg: string) => void;
}

export const ProfileView: React.FC<ProfileViewProps> = ({
  profile,
  onSelectFact,
  onRefreshData,
  showToast,
}) => {
  const [activeTab, setActiveTab] = useState<
    'overview' | 'financials' | 'people' | 'contact' | 'evidence' | 'history'
  >('overview');

  const [isTracked, setIsTracked] = useState(profile.is_tracked ?? false);

  const downloadJson = () => {
    const dataStr =
      'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(profile, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `${profile.org_number}_profile.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
    showToast('Exported company profile JSON');
  };

  const copyProfileLink = () => {
    const url = `${window.location.origin}/?orgnr=${profile.org_number}`;
    navigator.clipboard.writeText(url).then(
      () => showToast(`Copied share link for ${profile.org_number}!`),
      () => showToast('Failed to copy link')
    );
  };

  const handleToggleTrack = async () => {
    try {
      const res = await fetch(`/api/companies/${profile.org_number}/track`, { method: 'PATCH' });
      if (res.ok) {
        const data = await res.json();
        setIsTracked(data.is_tracked);
        showToast(
          data.is_tracked
            ? `Added ${profile.legal_name} to watchlist`
            : `Removed ${profile.legal_name} from watchlist`
        );
      }
    } catch {
      showToast('Failed to update watchlist');
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'ACTIVE':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-semibold">
            <CheckCircle className="w-3.5 h-3.5" />
            <span>Active Operations</span>
          </span>
        );
      case 'BANKRUPT':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 text-xs font-semibold">
            <AlertOctagon className="w-3.5 h-3.5" />
            <span>Bankrupt (Konkurs)</span>
          </span>
        );
      case 'IN_LIQUIDATION':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 text-xs font-semibold">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>In Liquidation</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700 text-xs font-semibold">
            <span>{status}</span>
          </span>
        );
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-in fade-in duration-300">
      {/* 1. Header Card */}
      <div className="p-6 sm:p-8 rounded-3xl glass-panel relative overflow-hidden border border-slate-200 dark:border-slate-800 shadow-xl dark:shadow-2xl">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="text-xs font-mono font-bold px-2.5 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/20">
                {profile.org_number}
              </span>
              <span className="text-xs px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800/80 text-slate-700 dark:text-slate-300 font-medium border border-slate-200 dark:border-transparent">
                {profile.org_form}
              </span>
              {getStatusBadge(profile.status)}
              <button
                onClick={handleToggleTrack}
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors cursor-pointer ${
                  isTracked
                    ? 'bg-amber-500/20 text-amber-700 dark:text-amber-300 border-amber-500/30'
                    : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-700 hover:text-slate-900 dark:hover:text-white shadow-sm'
                }`}
              >
                <Star className={`w-3.5 h-3.5 ${isTracked ? 'fill-amber-400 text-amber-500 dark:text-amber-400' : ''}`} />
                <span>{isTracked ? 'Watchlist' : 'Track'}</span>
              </button>
            </div>

            <h1 className="text-2xl sm:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              {profile.legal_name}
            </h1>

            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-600 dark:text-slate-400">
              <span className="flex items-center gap-1.5">
                <MapPin className="w-4 h-4 text-slate-400 dark:text-slate-500" />
                <span>{profile.address || 'Address registered in Norway'}</span>
                {profile.municipality && <span>&bull; {profile.municipality}</span>}
              </span>

              <span className="flex items-center gap-1.5">
                <Clock className="w-4 h-4 text-slate-400 dark:text-slate-500" />
                <span>
                  Updated {new Date(profile.last_checked_at).toLocaleDateString()}
                </span>
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400 font-semibold border border-emerald-200 dark:border-emerald-500/20">
                  Verified Fresh
                </span>
              </span>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => onRefreshData(profile.org_number)}
              className="flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 transition-colors cursor-pointer shadow-sm"
            >
              <RefreshCw className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
              <span>Refresh data</span>
            </button>

            <button
              onClick={copyProfileLink}
              className="flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 transition-colors cursor-pointer shadow-sm"
            >
              <Copy className="w-3.5 h-3.5 text-slate-400" />
              <span>Copy link</span>
            </button>

            <button
              onClick={downloadJson}
              className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-bold text-white shadow-md shadow-indigo-600/30 transition-all cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export JSON</span>
            </button>
          </div>
        </div>

        {/* Quick Highlights Bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-8 pt-6 border-t border-slate-200 dark:border-slate-800/80">
          <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
            <span className="text-[11px] text-slate-500 dark:text-slate-400 block mb-1">Registered Employees</span>
            <div className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-1.5 font-mono">
              <Users className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
              <span>
                {profile.employees !== null && profile.employees !== undefined
                  ? profile.employees.toLocaleString()
                  : 'N/A'}
              </span>
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
            <span className="text-[11px] text-slate-500 dark:text-slate-400 block mb-1">VAT / MVA Status</span>
            <div className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-1.5 font-mono">
              <CheckCircle
                className={`w-4 h-4 ${profile.vat_registered ? 'text-emerald-500 dark:text-emerald-400' : 'text-slate-400 dark:text-slate-500'}`}
              />
              <span>{profile.vat_registered ? 'Registered' : 'Exempt / No'}</span>
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
            <span className="text-[11px] text-slate-500 dark:text-slate-400 block mb-1">Registration Date</span>
            <div className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-1.5 font-mono">
              <Calendar className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
              <span>{profile.registered_date || 'N/A'}</span>
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
            <span className="text-[11px] text-slate-500 dark:text-slate-400 block mb-1">Verified Evidence Facts</span>
            <div className="text-base font-bold text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5 font-mono">
              <ShieldCheck className="w-4 h-4 text-emerald-500 dark:text-emerald-400" />
              <span>{profile.facts.length} facts</span>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Navigation Tabs (Overview, Financials, People, Website & Contact, Evidence, History) */}
      <div className="flex border-b border-slate-200 dark:border-slate-800 overflow-x-auto gap-2">
        {[
          { id: 'overview', label: 'Overview', icon: Building2 },
          { id: 'financials', label: 'Financials', icon: DollarSign },
          { id: 'people', label: 'People & Roles', icon: Briefcase },
          { id: 'contact', label: 'Website & Contact', icon: Globe },
          { id: 'evidence', label: 'Evidence & Provenance', icon: ShieldCheck },
          { id: 'history', label: 'Diff History', icon: History },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 py-3 px-4 text-xs font-bold border-b-2 transition-all cursor-pointer whitespace-nowrap ${
                isActive
                  ? 'border-indigo-600 dark:border-indigo-500 text-indigo-700 dark:text-white bg-indigo-50/70 dark:bg-slate-900/40 rounded-t-lg'
                  : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:border-slate-300 dark:hover:border-slate-700'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
              {tab.id === 'evidence' && (
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-indigo-100 text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-300 font-mono">
                  {profile.facts.length}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* 3. TAB 1: OVERVIEW */}
      {activeTab === 'overview' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          {/* Executive Summary */}
          {profile.description && (
            <div className="p-6 rounded-2xl glass-panel space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Business Profile &amp; Mission
              </h3>
              <p className="text-sm text-slate-700 dark:text-slate-200 leading-relaxed font-sans">
                {profile.description}
              </p>
            </div>
          )}

          {/* Industry NACE Classification */}
          {profile.nace_codes && profile.nace_codes.length > 0 && (
            <div className="p-6 rounded-2xl glass-panel space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Industry Classifications (NACE)
              </h3>
              <div className="flex flex-wrap gap-2">
                {profile.nace_codes.map((nace, idx) => (
                  <span
                    key={idx}
                    className="px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 text-xs text-slate-700 dark:text-slate-300 font-mono"
                  >
                    {nace}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Key Facts Summary Grid */}
          <div className="p-6 rounded-2xl glass-panel space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Verified Legal Facts
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {profile.facts.slice(0, 9).map((fact, idx) => (
                <div
                  key={idx}
                  onClick={() => onSelectFact(fact)}
                  className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 hover:border-indigo-500/50 hover:bg-slate-100/70 dark:hover:bg-slate-800/40 transition-all cursor-pointer group space-y-1.5"
                >
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="font-mono text-slate-500 dark:text-slate-400 capitalize">
                      {fact.field.replace(/_/g, ' ')}
                    </span>
                    <span className="text-emerald-600 dark:text-emerald-400 font-bold font-mono text-[10px]">
                      {Math.round(fact.confidence * 100)}% verified
                    </span>
                  </div>
                  <div className="text-xs font-semibold text-slate-900 dark:text-white truncate">
                    {typeof fact.value === 'object'
                      ? JSON.stringify(fact.value)
                      : String(fact.value)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 4. TAB 2: FINANCIALS */}
      {activeTab === 'financials' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          {/* Recharts Financial Chart */}
          <FinancialChart financials={profile.financials} />

          {/* Detailed Verbatim Table */}
          <div className="p-6 rounded-2xl glass-panel space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Official Annual Accounts Statement Table
              </h3>
              <span className="text-[11px] text-slate-500 font-mono">
                Source: Regnskapsregisteret Open Data (Verbatim)
              </span>
            </div>

            {profile.financials.length === 0 ? (
              <p className="text-xs text-slate-500 py-4 text-center">
                No annual statements registered with Brønnøysundregistrene.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-slate-100 dark:bg-slate-900/80 text-slate-700 dark:text-slate-400 uppercase text-[11px] border-b border-slate-200 dark:border-slate-800">
                    <tr>
                      <th className="py-2.5 px-3">Year</th>
                      <th className="py-2.5 px-3">Revenue (Salgsinntekter)</th>
                      <th className="py-2.5 px-3">Operating Profit (Driftsresultat)</th>
                      <th className="py-2.5 px-3">Net Profit (Årsresultat)</th>
                      <th className="py-2.5 px-3">Total Assets (Sum eiendeler)</th>
                      <th className="py-2.5 px-3">Equity (Egenkapital)</th>
                      <th className="py-2.5 px-3 text-right">Source</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-slate-700 dark:text-slate-300">
                    {profile.financials.map((f) => (
                      <tr key={f.year} className="hover:bg-slate-100/70 dark:hover:bg-slate-800/40">
                        <td className="py-3 px-3 font-bold text-slate-900 dark:text-white">{f.year}</td>
                        <td className="py-3 px-3">
                          {f.revenue ? `${f.revenue.toLocaleString()} ${f.currency}` : '—'}
                        </td>
                        <td className="py-3 px-3">
                          {f.operating_profit
                            ? `${f.operating_profit.toLocaleString()} ${f.currency}`
                            : '—'}
                        </td>
                        <td className="py-3 px-3">
                          {f.net_profit ? `${f.net_profit.toLocaleString()} ${f.currency}` : '—'}
                        </td>
                        <td className="py-3 px-3">
                          {f.assets ? `${f.assets.toLocaleString()} ${f.currency}` : '—'}
                        </td>
                        <td className="py-3 px-3">
                          {f.equity ? `${f.equity.toLocaleString()} ${f.currency}` : '—'}
                        </td>
                        <td className="py-3 px-3 text-right">
                          <a
                            href={f.source_url}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 font-semibold"
                          >
                            <span>Regnskap</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 5. TAB 3: PEOPLE & ROLES */}
      {activeTab === 'people' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          <div className="p-6 rounded-2xl glass-panel space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 pb-2 border-b border-slate-200 dark:border-slate-800">
              Registered Corporate Appointments &amp; Board Members
            </h3>

            {profile.roles.length === 0 ? (
              <p className="text-xs text-slate-500 py-4 text-center">
                No active roles filed in Enhetsregisteret for this entity.
              </p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {profile.roles.map((r, idx) => (
                  <div
                    key={idx}
                    className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 space-y-1.5"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-slate-900 dark:text-white">{r.name}</span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-indigo-50 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/20 font-semibold">
                        {r.role}
                      </span>
                    </div>
                    {r.from_date && (
                      <p className="text-[11px] text-slate-500 dark:text-slate-400">
                        Appointed: {new Date(r.from_date).toLocaleDateString()}
                      </p>
                    )}
                    {r.resigned && (
                      <span className="text-[10px] text-rose-600 dark:text-rose-400 font-semibold block">
                        Resigned / Former
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 6. TAB 4: WEBSITE & CONTACT */}
      {activeTab === 'contact' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Direct Contact Info */}
            <div className="p-6 rounded-2xl glass-panel space-y-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 pb-2 border-b border-slate-200 dark:border-slate-800">
                Verified Contact Details
              </h3>

              <div className="space-y-3 text-xs text-slate-700 dark:text-slate-300">
                <div className="flex items-center gap-3">
                  <Globe className="w-4 h-4 text-indigo-600 dark:text-indigo-400 flex-shrink-0" />
                  {profile.website ? (
                    <a
                      href={profile.website}
                      target="_blank"
                      rel="noreferrer"
                      className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 underline font-mono flex items-center gap-1 font-semibold"
                    >
                      <span>{profile.website}</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  ) : (
                    <span className="text-slate-400 dark:text-slate-500">No website registered</span>
                  )}
                </div>

                <div className="flex items-center gap-3">
                  <Mail className="w-4 h-4 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
                  {profile.contact.email ? (
                    <a
                      href={`mailto:${profile.contact.email}`}
                      className="text-slate-900 dark:text-slate-200 hover:underline font-mono"
                    >
                      {profile.contact.email}
                    </a>
                  ) : (
                    <span className="text-slate-400 dark:text-slate-500">No public email discovered</span>
                  )}
                </div>

                <div className="flex items-center gap-3">
                  <Phone className="w-4 h-4 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
                  {profile.contact.phone ? (
                    <span className="font-mono text-slate-900 dark:text-slate-200">{profile.contact.phone}</span>
                  ) : (
                    <span className="text-slate-400 dark:text-slate-500">No phone number on record</span>
                  )}
                </div>

                <div className="flex items-start gap-3">
                  <MapPin className="w-4 h-4 text-slate-400 dark:text-slate-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <span className="text-slate-900 dark:text-slate-200 block">
                      {profile.address || profile.contact.visiting_address || 'Norway'}
                    </span>
                    {profile.municipality && (
                      <span className="text-slate-500 dark:text-slate-400 text-[11px]">
                        Municipality: {profile.municipality} (code: {profile.municipality_number || 'N/A'})
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Social Media Links */}
            <div className="p-6 rounded-2xl glass-panel space-y-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 pb-2 border-b border-slate-200 dark:border-slate-800">
                Verified Social Links
              </h3>

              {profile.social_links.length === 0 ? (
                <p className="text-xs text-slate-500 py-4 text-center">
                  No verified social profiles found matching company domain.
                </p>
              ) : (
                <div className="space-y-2">
                  {profile.social_links.map((link, idx) => (
                    <a
                      key={idx}
                      href={link}
                      target="_blank"
                      rel="noreferrer"
                      className="p-3 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 hover:border-indigo-500/50 hover:bg-slate-100/70 dark:hover:bg-slate-800/40 flex items-center justify-between text-xs text-indigo-600 dark:text-indigo-400 transition-colors"
                    >
                      <span className="truncate max-w-xs font-mono">{link}</span>
                      <ExternalLink className="w-3.5 h-3.5 flex-shrink-0" />
                    </a>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 7. TAB 5: EVIDENCE & PROVENANCE */}
      {activeTab === 'evidence' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          <div className="p-6 rounded-2xl glass-panel space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Full Fact Provenance &amp; Verification Audit ({profile.facts.length} Verified Facts)
              </h3>
              <span className="text-[11px] text-slate-500">
                Click any fact card to inspect verbatim evidence quote and signals
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {profile.facts.map((fact, idx) => (
                <div
                  key={idx}
                  onClick={() => onSelectFact(fact)}
                  className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 hover:border-indigo-500/50 hover:bg-slate-100/70 dark:hover:bg-slate-800/40 transition-all cursor-pointer group space-y-2"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-mono font-bold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-300 transition-colors">
                      {fact.field}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20 font-bold">
                      {Math.round(fact.confidence * 100)}% verified
                    </span>
                  </div>

                  <p className="text-xs text-slate-700 dark:text-slate-300 font-mono truncate">
                    {typeof fact.value === 'object'
                      ? JSON.stringify(fact.value)
                      : String(fact.value)}
                  </p>

                  <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-200 dark:border-slate-800/60">
                    <span className="truncate max-w-[200px]">{fact.source_type}</span>
                    <span className="text-indigo-600 dark:text-indigo-400 group-hover:underline font-semibold">
                      Why this fact? &rarr;
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Rejected Facts Guardrail Safety Log */}
          {profile.rejected_facts.length > 0 && (
            <div className="p-6 rounded-2xl glass-panel border border-rose-200 dark:border-rose-500/20 space-y-4">
              <div className="flex items-center gap-2 text-rose-600 dark:text-rose-400">
                <AlertOctagon className="w-4 h-4" />
                <h3 className="text-xs font-bold uppercase tracking-wider">
                  Rejected Candidate Facts ({profile.rejected_facts.length} Guardrail Interceptions)
                </h3>
              </div>

              <div className="space-y-2">
                {profile.rejected_facts.map((rf, idx) => (
                  <div
                    key={idx}
                    className="p-3.5 rounded-xl bg-rose-50/70 dark:bg-rose-500/5 border border-rose-200 dark:border-rose-500/10 text-xs space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-rose-700 dark:text-rose-300">{rf.field}</span>
                      <span className="text-[10px] text-slate-500 font-mono">
                        Candidate Value: {String(rf.candidate_value)}
                      </span>
                    </div>
                    <p className="text-slate-600 dark:text-slate-400 text-[11px]">Reason: {rf.reason}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* 8. TAB 6: DIFF HISTORY */}
      {activeTab === 'history' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          <div className="p-6 rounded-2xl glass-panel space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 pb-2 border-b border-slate-200 dark:border-slate-800">
              Audit Version Revisions &amp; Field Diffs
            </h3>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Revision reference: <span className="font-mono text-indigo-600 dark:text-indigo-400 font-semibold">{profile.history_ref || 'Initial Baseline Version'}</span>
            </p>
            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 text-xs text-slate-700 dark:text-slate-300">
              Every re-run computes SHA-256 hashes of new facts and appends revision diffs to the audit trail. Unchanged facts remain verified and are never silently overwritten.
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
