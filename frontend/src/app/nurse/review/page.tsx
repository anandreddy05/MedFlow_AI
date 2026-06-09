'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { useState, Suspense } from 'react';
import { 
  ArrowLeft, 
  Check, 
  X,
  FileText,
  Activity,
  TrendingUp,
  TrendingDown,
  AlertCircle
} from 'lucide-react';

// Mock data for review
const mockDocument = {
  document_id: '1',
  patient_id: 'MRN-2024-001234',
  patient_name: 'John Smith',
  report_type: 'cbc',
  extracted_data: {
    patient_name: 'John Smith',
    collection_date: '2024-01-15',
    results: [
      { test_name: 'Hemoglobin', value: 14.5, unit: 'g/dL', reference_range_min: 13.5, reference_range_max: 17.5, flag: 'Normal', confidence: 0.95 },
      { test_name: 'White Blood Cell Count', value: 11.2, unit: 'x10^3/uL', reference_range_min: 4.5, reference_range_max: 11.0, flag: 'High', confidence: 0.92 },
      { test_name: 'Platelet Count', value: 250, unit: 'x10^3/uL', reference_range_min: 150, reference_range_max: 450, flag: 'Normal', confidence: 0.94 },
      { test_name: 'Red Blood Cell Count', value: 4.8, unit: 'x10^6/uL', reference_range_min: 4.5, reference_range_max: 5.9, flag: 'Normal', confidence: 0.91 },
    ]
  }
};

function NurseReviewContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const documentId = searchParams.get('id') || '1';
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [data] = useState(mockDocument.extracted_data);

  const handleApprove = async () => {
    setIsSubmitting(true);
    await new Promise(resolve => setTimeout(resolve, 1500));
    alert('Document approved successfully!');
    router.push('/nurse/pending');
    setIsSubmitting(false);
  };

  const handleReject = () => {
    if (confirm('Are you sure you want to reject this document?')) {
      router.push('/nurse/pending');
    }
  };

  const getFlagColor = (flag: string) => {
    switch(flag) {
      case 'High': return 'text-red-600 bg-red-50 border-red-200';
      case 'Low': return 'text-orange-600 bg-orange-50 border-orange-200';
      default: return 'text-green-600 bg-green-50 border-green-200';
    }
  };

  const getFlagIcon = (flag: string) => {
    switch(flag) {
      case 'High': return <TrendingUp className="w-3 h-3" />;
      case 'Low': return <TrendingDown className="w-3 h-3" />;
      default: return <Check className="w-3 h-3" />;
    }
  };

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-6">
        <button
          onClick={() => router.back()}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Pending Reviews
        </button>
        
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Review Medical Document</h1>
            <p className="text-gray-600 mt-1">
              Patient: {mockDocument.patient_name} (MRN: {mockDocument.patient_id})
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={handleReject}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center gap-2"
            >
              <X className="w-4 h-4" />
              Reject
            </button>
            <button
              onClick={handleApprove}
              disabled={isSubmitting}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center gap-2 disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Processing...
                </>
              ) : (
                <>
                  <Check className="w-4 h-4" />
                  Approve Document
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Panel - Original Document */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
            <h2 className="font-semibold text-gray-900 flex items-center gap-2">
              <FileText className="w-4 h-4 text-blue-600" />
              Original Document
            </h2>
          </div>
          <div className="p-6 min-h-[500px] flex items-center justify-center">
            <div className="text-center">
              <div className="w-20 h-20 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <FileText className="w-10 h-10 text-gray-400" />
              </div>
              <p className="text-gray-500">Document Preview</p>
              <p className="text-sm text-gray-400 mt-2">PDF/Image would appear here</p>
            </div>
          </div>
        </div>

        {/* Right Panel - AI Extracted Data */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
            <h2 className="font-semibold text-gray-900 flex items-center gap-2">
              <Activity className="w-4 h-4 text-purple-600" />
              AI-Extracted Data
            </h2>
          </div>
          <div className="p-6">
            <div className="mb-6 grid grid-cols-2 gap-4 p-4 bg-gray-50 rounded-lg">
              <div>
                <label className="text-xs text-gray-500">Patient Name</label>
                <p className="font-medium text-gray-900 mt-1">{data.patient_name}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500">Collection Date</label>
                <p className="font-medium text-gray-900 mt-1">{data.collection_date}</p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b border-gray-200">
                  <tr>
                    <th className="text-left pb-3 text-sm font-medium text-gray-700">Test Name</th>
                    <th className="text-left pb-3 text-sm font-medium text-gray-700">Value</th>
                    <th className="text-left pb-3 text-sm font-medium text-gray-700">Unit</th>
                    <th className="text-left pb-3 text-sm font-medium text-gray-700">Reference</th>
                    <th className="text-left pb-3 text-sm font-medium text-gray-700">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {data.results.map((result, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="py-3 text-sm text-gray-900">{result.test_name}</td>
                      <td className={`py-3 text-sm font-medium ${result.flag === 'High' ? 'text-red-600' : result.flag === 'Low' ? 'text-orange-600' : 'text-gray-900'}`}>
                        {result.value}
                      </td>
                      <td className="py-3 text-sm text-gray-600">{result.unit}</td>
                      <td className="py-3 text-sm text-gray-600">
                        {result.reference_range_min} - {result.reference_range_max}
                      </td>
                      <td className="py-3">
                        <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs border ${getFlagColor(result.flag)}`}>
                          {getFlagIcon(result.flag)}
                          {result.flag}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function NurseReviewPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-screen">
          <p className="text-gray-500">Loading review...</p>
        </div>
      }
    >
      <NurseReviewContent />
    </Suspense>
  );
}
