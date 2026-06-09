'use client';

import { useState, useEffect } from 'react';
import { API_BASE_URL } from '@/lib/api/client';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { 
  FileText, 
  Clock, 
  AlertCircle, 
  CheckCircle,
  Search,
  Eye
} from 'lucide-react';

interface PendingReport {
  document_id: string;
  patient_id: string;
  patient_name?: string;
  report_type: string;
  created_at: string;
  has_original_file: boolean;
  extracted_data?: any;
  content_markdown?: string;
}

export default function NursePendingPage() {
  const router = useRouter();
  const [pendingReports, setPendingReports] = useState<PendingReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    fetchPendingReports();
  }, []);

  const fetchPendingReports = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_BASE_URL}/reports/pending`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      
      if (response.ok) {
        const data = await response.json();
        setPendingReports(data.pending_reports || []);
      } else {
        setError('Failed to fetch pending reports');
      }
    } catch (error) {
      console.error('Error fetching pending reports:', error);
      setError('Network error');
    } finally {
      setLoading(false);
    }
  };

  const getReportTypeLabel = (type: string) => {
    const types: Record<string, string> = {
      cbc: 'CBC Report',
      digital_prescription: 'Prescription',
      discharge_summary: 'Discharge Summary',
      medical_invoice: 'Medical Invoice',
    };
    return types[type] || type;
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return 'Unknown';
    return new Date(dateString).toLocaleString();
  };

  const filteredReports = pendingReports.filter(report => 
    report.patient_id?.toLowerCase().includes(search.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
        {error}
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Pending Reviews</h1>
        <p className="text-gray-600 mt-1">Review and validate AI-extracted medical data</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search by patient ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {pendingReports.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-1">All caught up!</h3>
          <p className="text-gray-600">No pending reports to review.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredReports.map((report, index) => (
            <motion.div
              key={report.document_id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-all cursor-pointer"
              onClick={() => router.push(`/nurse/review/${report.document_id}`)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-gray-100 rounded-xl flex items-center justify-center">
                    <FileText className="w-6 h-6 text-gray-500" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-semibold text-gray-900">
                        Patient ID: {report.patient_id}
                      </h3>
                    </div>
                    <p className="text-sm text-gray-600">{getReportTypeLabel(report.report_type)}</p>
                    <p className="text-xs text-gray-400 mt-1">
                      Uploaded: {formatDate(report.created_at)}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700">
                    <Clock className="w-3 h-3" />
                    Pending
                  </span>
                  <button className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
                    <Eye className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
