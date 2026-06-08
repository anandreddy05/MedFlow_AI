'use client';

import { useState, useEffect, useMemo } from 'react';
import {
  Shield,
  Search,
  RefreshCw,
  ClipboardList,
  FileCheck,
  Pill,
  ArrowRightLeft,
  Filter,
  Calendar,
  Mail,
  FileText,
  Loader2,
} from 'lucide-react';

type AuditLog = {
  log_id: number;
  user_email: string;
  action: string;
  document_id: string;
  timestamp: string | null;
};

const ACTION_STYLES: Record<string, { label: string; bg: string; text: string; icon: typeof Shield }> = {
  APPROVED_REPORT: { label: 'Report Approved', bg: 'bg-emerald-50', text: 'text-emerald-700', icon: FileCheck },
  DIRECT_ENTRY_PRESCRIPTION: { label: 'Prescription Created', bg: 'bg-blue-50', text: 'text-blue-700', icon: Pill },
  TRANSFER_PATIENT: { label: 'Patient Transfer', bg: 'bg-violet-50', text: 'text-violet-700', icon: ArrowRightLeft },
};

function getActionStyle(action: string) {
  const key = Object.keys(ACTION_STYLES).find((k) => action.includes(k));
  if (key) return ACTION_STYLES[key];
  return { label: action.replace(/_/g, ' '), bg: 'bg-slate-50', text: 'text-slate-700', icon: ClipboardList };
}

function formatTimestamp(ts: string | null) {
  if (!ts) return '—';
  const date = new Date(ts);
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function isToday(ts: string | null) {
  if (!ts) return false;
  const d = new Date(ts);
  const now = new Date();
  return d.toDateString() === now.toDateString();
}

export default function AdminAuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [search, setSearch] = useState('');
  const [actionFilter, setActionFilter] = useState('all');
  const [limit, setLimit] = useState(100);

  const fetchLogs = async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true);
    else setLoading(true);

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`http://localhost:8000/admin/logs?limit=${limit}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setLogs(data.logs || []);
      }
    } catch (error) {
      console.error('Failed to fetch audit logs:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [limit]);

  const actionTypes = useMemo(() => {
    const types = new Set(logs.map((l) => l.action));
    return Array.from(types).sort();
  }, [logs]);

  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      const matchesSearch =
        !search ||
        log.user_email.toLowerCase().includes(search.toLowerCase()) ||
        log.action.toLowerCase().includes(search.toLowerCase()) ||
        log.document_id.toLowerCase().includes(search.toLowerCase());
      const matchesAction = actionFilter === 'all' || log.action === actionFilter;
      return matchesSearch && matchesAction;
    });
  }, [logs, search, actionFilter]);

  const stats = useMemo(() => ({
    total: logs.length,
    today: logs.filter((l) => isToday(l.timestamp)).length,
    uniqueActions: new Set(logs.map((l) => l.action)).size,
  }), [logs]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50/30 p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8 flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2.5 bg-indigo-600 rounded-xl shadow-lg shadow-indigo-200">
                <Shield className="w-6 h-6 text-white" />
              </div>
              <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Audit Logs</h1>
            </div>
            <p className="text-gray-600 ml-14">
              Compliance trail of system actions — who did what, and when.
            </p>
          </div>
          <button
            onClick={() => fetchLogs(true)}
            disabled={refreshing}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50 shadow-sm transition-all disabled:opacity-60"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          <div className="bg-white/80 backdrop-blur rounded-2xl border border-gray-100 p-5 shadow-sm">
            <p className="text-sm font-medium text-gray-500">Total Events</p>
            <p className="text-3xl font-bold text-gray-900 mt-1">{stats.total}</p>
          </div>
          <div className="bg-white/80 backdrop-blur rounded-2xl border border-gray-100 p-5 shadow-sm">
            <p className="text-sm font-medium text-gray-500">Today</p>
            <p className="text-3xl font-bold text-indigo-600 mt-1">{stats.today}</p>
          </div>
          <div className="bg-white/80 backdrop-blur rounded-2xl border border-gray-100 p-5 shadow-sm">
            <p className="text-sm font-medium text-gray-500">Action Types</p>
            <p className="text-3xl font-bold text-gray-900 mt-1">{stats.uniqueActions}</p>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 mb-6 flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search by email, action, or document ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400"
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400 shrink-0" />
            <select
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="px-3 py-2.5 border border-gray-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
            >
              <option value="all">All actions</option>
              {actionTypes.map((action) => (
                <option key={action} value={action}>
                  {action.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
            <select
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="px-3 py-2.5 border border-gray-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
            >
              <option value={50}>Last 50</option>
              <option value={100}>Last 100</option>
              <option value={200}>Last 200</option>
            </select>
          </div>
        </div>

        {/* Logs list */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 text-gray-500">
              <Loader2 className="w-8 h-8 animate-spin text-indigo-500 mb-3" />
              <p className="text-sm">Loading audit logs...</p>
            </div>
          ) : filteredLogs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-gray-500">
              <ClipboardList className="w-12 h-12 text-gray-300 mb-3" />
              <p className="font-medium text-gray-700">No audit logs found</p>
              <p className="text-sm mt-1">Actions will appear here as users interact with the system.</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-50">
              {filteredLogs.map((log) => {
                const style = getActionStyle(log.action);
                const Icon = style.icon;
                return (
                  <div
                    key={log.log_id}
                    className="p-5 hover:bg-slate-50/80 transition-colors group"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-start gap-4">
                      <div className={`shrink-0 p-3 rounded-xl ${style.bg}`}>
                        <Icon className={`w-5 h-5 ${style.text}`} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2 mb-1">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${style.bg} ${style.text}`}>
                            {style.label}
                          </span>
                          <span className="text-xs text-gray-400 font-mono">#{log.log_id}</span>
                        </div>
                        <p className="text-sm font-medium text-gray-800 mb-2">{log.action}</p>
                        <div className="flex flex-wrap gap-x-5 gap-y-1 text-sm text-gray-500">
                          <span className="inline-flex items-center gap-1.5">
                            <Mail className="w-3.5 h-3.5" />
                            {log.user_email}
                          </span>
                          <span className="inline-flex items-center gap-1.5">
                            <FileText className="w-3.5 h-3.5" />
                            <span className="truncate max-w-[240px]" title={log.document_id}>
                              {log.document_id}
                            </span>
                          </span>
                          <span className="inline-flex items-center gap-1.5">
                            <Calendar className="w-3.5 h-3.5" />
                            {formatTimestamp(log.timestamp)}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {!loading && filteredLogs.length > 0 && (
          <p className="text-center text-xs text-gray-400 mt-4">
            Showing {filteredLogs.length} of {logs.length} loaded events
          </p>
        )}
      </div>
    </div>
  );
}
