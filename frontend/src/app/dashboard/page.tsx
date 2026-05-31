'use client';

import { useAuth } from '@/lib/hooks/useAuth';
import { Activity, Users, FileText, Clock, TrendingUp } from 'lucide-react';

export default function DashboardPage() {
  const { user } = useAuth();

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600 mt-1">
          Welcome back, {user?.email}!
        </p>
        <p className="text-sm text-gray-500">Role: {user?.role}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div className="p-2 bg-blue-50 rounded-lg">
              <Users className="w-5 h-5 text-blue-600" />
            </div>
            <span className="text-xs text-green-600">+12%</span>
          </div>
          <p className="text-2xl font-bold mt-4">0</p>
          <p className="text-sm text-gray-600 mt-1">Total Patients</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div className="p-2 bg-emerald-50 rounded-lg">
              <FileText className="w-5 h-5 text-emerald-600" />
            </div>
            <span className="text-xs text-green-600">+8%</span>
          </div>
          <p className="text-2xl font-bold mt-4">0</p>
          <p className="text-sm text-gray-600 mt-1">Documents</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div className="p-2 bg-amber-50 rounded-lg">
              <Clock className="w-5 h-5 text-amber-600" />
            </div>
            <span className="text-xs text-red-600">-5%</span>
          </div>
          <p className="text-2xl font-bold mt-4">0</p>
          <p className="text-sm text-gray-600 mt-1">Pending Reviews</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div className="p-2 bg-purple-50 rounded-lg">
              <Activity className="w-5 h-5 text-purple-600" />
            </div>
            <span className="text-xs text-green-600">+2.3%</span>
          </div>
          <p className="text-2xl font-bold mt-4">94.8%</p>
          <p className="text-sm text-gray-600 mt-1">AI Accuracy</p>
        </div>
      </div>

      <div className="mt-8 bg-blue-50 border border-blue-200 rounded-xl p-6">
        <h3 className="font-semibold text-blue-900">MedFlow AI Ready</h3>
        <p className="text-blue-800 text-sm mt-1">
          Your healthcare intelligence platform is ready. Select an option from the sidebar.
        </p>
      </div>
    </div>
  );
}
