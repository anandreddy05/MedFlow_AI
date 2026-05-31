'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { 
  Activity, 
  FileText, 
  Clock, 
  Upload, 
  CheckCircle, 
  AlertCircle,
  TrendingUp,
  Users,
  ArrowRight
} from 'lucide-react';

export default function NurseDashboard() {
  const router = useRouter();
  const [stats] = useState({
    pendingReviews: 12,
    uploadedToday: 8,
    patientsSeen: 45,
    approvalRate: 94,
  });

  const recentActivities = [
    { id: 1, patient: 'John Smith', type: 'CBC Report', time: '5 min ago', status: 'pending', priority: 'high' },
    { id: 2, patient: 'Sarah Johnson', type: 'Prescription', time: '15 min ago', status: 'pending', priority: 'normal' },
    { id: 3, patient: 'Michael Brown', type: 'Discharge Summary', time: '1 hour ago', status: 'approved', priority: 'normal' },
    { id: 4, patient: 'Emily Davis', type: 'CBC Report', time: '2 hours ago', status: 'pending', priority: 'high' },
    { id: 5, patient: 'James Wilson', type: 'Medical Invoice', time: '3 hours ago', status: 'pending', priority: 'normal' },
  ];

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Nurse Dashboard</h1>
        <p className="text-gray-600 mt-1">
          Manage document uploads and review AI-extracted medical data
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <motion.div
          whileHover={{ y: -4 }}
          className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm hover:shadow-md transition-all"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="p-2 bg-yellow-50 rounded-lg">
              <Clock className="w-5 h-5 text-yellow-600" />
            </div>
            <span className="text-xs text-red-600">{stats.pendingReviews} pending</span>
          </div>
          <p className="text-2xl font-bold text-gray-900">{stats.pendingReviews}</p>
          <p className="text-sm text-gray-600 mt-1">Pending Reviews</p>
        </motion.div>

        <motion.div
          whileHover={{ y: -4 }}
          className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm hover:shadow-md transition-all"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="p-2 bg-blue-50 rounded-lg">
              <Upload className="w-5 h-5 text-blue-600" />
            </div>
            <span className="text-xs text-green-600">+{stats.uploadedToday} today</span>
          </div>
          <p className="text-2xl font-bold text-gray-900">{stats.uploadedToday}</p>
          <p className="text-sm text-gray-600 mt-1">Documents Uploaded</p>
        </motion.div>

        <motion.div
          whileHover={{ y: -4 }}
          className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm hover:shadow-md transition-all"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="p-2 bg-green-50 rounded-lg">
              <Users className="w-5 h-5 text-green-600" />
            </div>
            <span className="text-xs text-green-600">+12 this week</span>
          </div>
          <p className="text-2xl font-bold text-gray-900">{stats.patientsSeen}</p>
          <p className="text-sm text-gray-600 mt-1">Patients Seen</p>
        </motion.div>

        <motion.div
          whileHover={{ y: -4 }}
          className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm hover:shadow-md transition-all"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="p-2 bg-purple-50 rounded-lg">
              <CheckCircle className="w-5 h-5 text-purple-600" />
            </div>
            <span className="text-xs text-green-600">+2.3%</span>
          </div>
          <p className="text-2xl font-bold text-gray-900">{stats.approvalRate}%</p>
          <p className="text-sm text-gray-600 mt-1">Approval Rate</p>
        </motion.div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <motion.button
          whileHover={{ scale: 1.02 }}
          onClick={() => router.push('/nurse/upload')}
          className="col-span-1 bg-gradient-to-r from-blue-600 to-blue-700 rounded-xl p-6 text-white shadow-lg hover:shadow-xl transition-all"
        >
          <Upload className="w-8 h-8 mb-3" />
          <h3 className="text-lg font-semibold">Upload Document</h3>
          <p className="text-blue-100 text-sm mt-1">Upload patient reports and medical documents</p>
          <div className="flex items-center gap-2 mt-4 text-sm">
            <span>Start uploading</span>
            <ArrowRight className="w-4 h-4" />
          </div>
        </motion.button>

        <motion.button
          whileHover={{ scale: 1.02 }}
          onClick={() => router.push('/nurse/pending')}
          className="col-span-1 bg-white rounded-xl border border-gray-200 p-6 shadow-sm hover:shadow-md transition-all"
        >
          <Clock className="w-8 h-8 text-yellow-600 mb-3" />
          <h3 className="text-lg font-semibold text-gray-900">Review Documents</h3>
          <p className="text-gray-600 text-sm mt-1">Review and validate AI-extracted data</p>
          <div className="flex items-center gap-2 mt-4 text-sm text-blue-600">
            <span>{stats.pendingReviews} pending reviews</span>
            <ArrowRight className="w-4 h-4" />
          </div>
        </motion.button>

        <motion.button
          whileHover={{ scale: 1.02 }}
          className="col-span-1 bg-white rounded-xl border border-gray-200 p-6 shadow-sm hover:shadow-md transition-all"
        >
          <FileText className="w-8 h-8 text-green-600 mb-3" />
          <h3 className="text-lg font-semibold text-gray-900">View All Documents</h3>
          <p className="text-gray-600 text-sm mt-1">Browse all processed medical records</p>
          <div className="flex items-center gap-2 mt-4 text-sm text-blue-600">
            <span>View archive</span>
            <ArrowRight className="w-4 h-4" />
          </div>
        </motion.button>
      </div>

      {/* Recent Activity Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Recent Uploads</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">Patient</th>
                <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">Document Type</th>
                <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">Time</th>
                <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">Status</th>
                <th className="text-left px-6 py-3 text-sm font-medium text-gray-500"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {recentActivities.map((activity) => (
                <tr key={activity.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">{activity.patient}</td>
                  <td className="px-6 py-4 text-sm text-gray-600">{activity.type}</td>
                  <td className="px-6 py-4 text-sm text-gray-500">{activity.time}</td>
                  <td className="px-6 py-4">
                    {activity.status === 'pending' ? (
                      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                        activity.priority === 'high' 
                          ? 'bg-red-100 text-red-700' 
                          : 'bg-yellow-100 text-yellow-700'
                      }`}>
                        <AlertCircle className="w-3 h-3" />
                        Pending Review
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">
                        <CheckCircle className="w-3 h-3" />
                        Approved
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    {activity.status === 'pending' && (
                      <button
                        onClick={() => router.push(`/nurse/review/${activity.id}`)}
                        className="text-blue-600 hover:text-blue-700 text-sm font-medium"
                      >
                        Review →
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
