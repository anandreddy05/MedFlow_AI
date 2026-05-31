'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Users, FileText, Activity, Shield, Clock, AlertCircle } from 'lucide-react';

export default function AdminDashboard() {
  const router = useRouter();
  const [stats, setStats] = useState({
    totalUsers: 0,
    totalDocuments: 0,
    pendingReviews: 0,
    systemHealth: 99.9,
  });
  const [recentLogs, setRecentLogs] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch('http://localhost:8000/admin/logs?limit=10', {
          headers: { 'Authorization': `Bearer ${token}` },
        });
        if (response.ok) {
          const data = await response.json();
          setRecentLogs(data.logs || []);
        }
      } catch (error) {
        console.error('Failed to fetch admin data:', error);
      }
    };
    fetchData();
  }, []);

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
        <p className="text-gray-600 mt-1">System overview and compliance monitoring</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-xl border p-6">
          <div className="p-2 bg-blue-50 rounded-lg w-fit mb-4">
            <Users className="w-5 h-5 text-blue-600" />
          </div>
          <p className="text-2xl font-bold">{stats.totalUsers}</p>
          <p className="text-sm text-gray-600">Total Users</p>
        </div>

        <div className="bg-white rounded-xl border p-6">
          <div className="p-2 bg-green-50 rounded-lg w-fit mb-4">
            <FileText className="w-5 h-5 text-green-600" />
          </div>
          <p className="text-2xl font-bold">{stats.totalDocuments}</p>
          <p className="text-sm text-gray-600">Documents Processed</p>
        </div>

        <div className="bg-white rounded-xl border p-6">
          <div className="p-2 bg-yellow-50 rounded-lg w-fit mb-4">
            <Clock className="w-5 h-5 text-yellow-600" />
          </div>
          <p className="text-2xl font-bold">{stats.pendingReviews}</p>
          <p className="text-sm text-gray-600">Pending Reviews</p>
        </div>

        <div className="bg-white rounded-xl border p-6">
          <div className="p-2 bg-purple-50 rounded-lg w-fit mb-4">
            <Activity className="w-5 h-5 text-purple-600" />
          </div>
          <p className="text-2xl font-bold">{stats.systemHealth}%</p>
          <p className="text-sm text-gray-600">System Health</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border">
          <div className="p-4 border-b">
            <h3 className="font-semibold flex items-center gap-2">
              <Shield className="w-4 h-4" />
              Recent Audit Logs
            </h3>
          </div>
          <div className="divide-y">
            {recentLogs.length === 0 ? (
              <div className="p-8 text-center text-gray-500">No logs available</div>
            ) : (
              recentLogs.map((log: any, idx: number) => (
                <div key={idx} className="p-3 text-sm">
                  <p className="font-medium">{log.action}</p>
                  <p className="text-xs text-gray-500">
                    User: {log.user_email} • {new Date(log.timestamp).toLocaleString()}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="bg-white rounded-xl border">
          <div className="p-4 border-b">
            <h3 className="font-semibold">Quick Actions</h3>
          </div>
          <div className="p-4 space-y-3">
            <button
              onClick={() => router.push('/registration')}
              className="w-full text-left px-4 py-2 bg-gray-50 rounded-lg hover:bg-gray-100"
            >
              Create New User
            </button>
            <button
              onClick={() => router.push('/admin/users')}
              className="w-full text-left px-4 py-2 bg-gray-50 rounded-lg hover:bg-gray-100"
            >
              Manage Users
            </button>
            <button
              onClick={() => router.push('/admin/audit-logs')}
              className="w-full text-left px-4 py-2 bg-gray-50 rounded-lg hover:bg-gray-100"
            >
              View Full Audit Log
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}