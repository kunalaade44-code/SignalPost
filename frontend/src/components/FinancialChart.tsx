import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from 'recharts';
import type { FinancialYear } from '../types';

interface FinancialChartProps {
  financials: FinancialYear[];
}

export const FinancialChart: React.FC<FinancialChartProps> = ({ financials }) => {
  if (!financials || financials.length === 0) {
    return (
      <div className="p-8 text-center text-slate-400 text-sm glass-panel rounded-2xl">
        No annual financial statements on record for this company.
      </div>
    );
  }

  // Sort by year ascending for chronological chart presentation
  const sorted = [...financials].sort((a, b) => a.year - b.year);

  // Determine scaling factor (Billions, Millions, or Thousands)
  const maxVal = Math.max(
    ...sorted.map((f) =>
      Math.max(
        Math.abs(f.revenue || 0),
        Math.abs(f.operating_profit || 0),
        Math.abs(f.net_profit || 0),
        Math.abs(f.equity || 0)
      )
    )
  );

  let scale = 1;
  let unit = 'NOK';
  if (maxVal >= 1_000_000_000) {
    scale = 1_000_000_000;
    unit = 'Billion NOK';
  } else if (maxVal >= 1_000_000) {
    scale = 1_000_000;
    unit = 'Million NOK';
  } else if (maxVal >= 1_000) {
    scale = 1_000;
    unit = 'Thousand NOK';
  }

  const chartData = sorted.map((f) => ({
    year: f.year.toString(),
    Revenue: f.revenue ? Number((f.revenue / scale).toFixed(2)) : 0,
    OperatingProfit: f.operating_profit ? Number((f.operating_profit / scale).toFixed(2)) : 0,
    NetProfit: f.net_profit ? Number((f.net_profit / scale).toFixed(2)) : 0,
    Equity: f.equity ? Number((f.equity / scale).toFixed(2)) : 0,
  }));

  const formatCurrency = (val: number) => {
    return `${val.toLocaleString()} ${unit}`;
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl p-3 shadow-xl text-xs space-y-1 z-50">
          <p className="font-bold text-slate-900 dark:text-white border-b border-slate-200 dark:border-slate-800 pb-1 mb-1 font-mono">
            Fiscal Year {label}
          </p>
          {payload.map((entry: any, index: number) => (
            <div key={index} className="flex items-center justify-between gap-4">
              <span className="flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
                <span className="w-2 h-2 rounded-full inline-block" style={{ backgroundColor: entry.color }} />
                <span>
                  {entry.name === 'OperatingProfit'
                    ? 'Operating Profit'
                    : entry.name === 'NetProfit'
                      ? 'Net Profit'
                      : entry.name}
                </span>
              </span>
              <span className="font-mono font-semibold text-slate-900 dark:text-white">
                {formatCurrency(Number(entry.value || 0))}
              </span>
            </div>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="p-6 rounded-2xl glass-panel space-y-4 border border-slate-200 dark:border-slate-800 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h4 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider">
            Financial Performance Overview
          </h4>
          <p className="text-xs text-slate-600 dark:text-slate-400">
            Official annual accounts from Regnskapsregisteret ({unit})
          </p>
        </div>
        <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-indigo-50 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/20 font-semibold">
          {sorted.length} Fiscal Years Reported
        </span>
      </div>

      <div className="h-72 w-full pt-4">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.25)" />
            <XAxis dataKey="year" stroke="#94a3b8" tick={{ fill: '#64748b', fontSize: 12 }} />
            <YAxis
              stroke="#94a3b8"
              tick={{ fill: '#64748b', fontSize: 11 }}
              tickFormatter={(v) => `${v}`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ paddingTop: '10px', fontSize: '0.75rem' }}
              formatter={(val) => (
                <span className="text-slate-700 dark:text-slate-300 font-medium">
                  {val === 'OperatingProfit'
                    ? 'Operating Profit'
                    : val === 'NetProfit'
                      ? 'Net Profit'
                      : val}
                </span>
              )}
            />
            <Bar dataKey="Revenue" fill="#6366f1" radius={[4, 4, 0, 0]} />
            <Bar dataKey="OperatingProfit" fill="#10b981" radius={[4, 4, 0, 0]} />
            <Bar dataKey="NetProfit" fill="#38bdf8" radius={[4, 4, 0, 0]} />
            <Bar dataKey="Equity" fill="#f59e0b" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
