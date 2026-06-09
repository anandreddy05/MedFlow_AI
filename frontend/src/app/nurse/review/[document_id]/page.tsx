'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Check, X, FileText, Image as ImageIcon, Edit2, Save, AlertCircle } from 'lucide-react';
import { API_BASE_URL } from '@/lib/api/client';

interface CBCResult {
  test_name: string;
  value: number;
  unit: string;
  reference_range_min: number | null;
  reference_range_max: number | null;
  flag: string;
}

interface DocumentData {
  document_id: string;
  patient_id: string;
  report_type: string;
  extracted_data: any;
  content_markdown: string;
  created_at: string;
  has_original_file: boolean;
}

export default function NurseReviewPage() {
  const { document_id } = useParams();
  const router = useRouter();
  const [document, setDocument] = useState<DocumentData | null>(null);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState(false);
  const [editedData, setEditedData] = useState<any>(null);
  const [editingCell, setEditingCell] = useState<{ row: number; field: string } | null>(null);
  const [editValue, setEditValue] = useState('');
  const [originalFileUrl, setOriginalFileUrl] = useState<string | null>(null);

  useEffect(() => {
    fetchDocument();
  }, [document_id]);

  const fetchDocument = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_BASE_URL}/reports/pending`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        const found = data.pending_reports?.find((r: any) => r.document_id === document_id);
        setDocument(found);
        setEditedData(found?.extracted_data);
        
        // Fetch original file URL
        if (found?.has_original_file) {
          const fileResponse = await fetch(`${API_BASE_URL}/documents/${document_id}/file`, {
            headers: { 'Authorization': `Bearer ${token}` },
          });
          if (fileResponse.ok) {
            const blob = await fileResponse.blob();
            const url = URL.createObjectURL(blob);
            setOriginalFileUrl(url);
          }
        }
      }
    } catch (error) {
      console.error('Error fetching document:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async () => {
    setApproving(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_BASE_URL}/reports/approve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          document_id: document_id,
          corrected_report: editedData,
        }),
      });
      
      if (response.ok) {
        alert('Document approved successfully! It will now be added to the knowledge base.');
        router.push('/nurse/pending');
      } else {
        alert('Failed to approve document');
      }
    } catch (error) {
      console.error('Error approving:', error);
      alert('Error approving document');
    } finally {
      setApproving(false);
    }
  };

  const handleReject = () => {
    if (confirm('Are you sure you want to reject this document?')) {
      router.push('/nurse/pending');
    }
  };

  const handleEdit = (rowIndex: number, field: string, currentValue: any) => {
    setEditingCell({ row: rowIndex, field });
    setEditValue(String(currentValue));
  };

  const handleSaveEdit = (rowIndex: number, field: string) => {
    const newResults = [...(editedData?.results || [])];
    let parsedValue: any = editValue;
    
    if (field === 'value') {
      parsedValue = parseFloat(editValue);
    }
    
    newResults[rowIndex] = { ...newResults[rowIndex], [field]: parsedValue };
    
    // Update flag based on new value
    if (field === 'value') {
      const result = newResults[rowIndex];
      const isHigh = result.reference_range_max && parsedValue > result.reference_range_max;
      const isLow = result.reference_range_min && parsedValue < result.reference_range_min;
      newResults[rowIndex].flag = isHigh ? 'High' : isLow ? 'Low' : 'Normal';
    }
    
    setEditedData({ ...editedData, results: newResults });
    setEditingCell(null);
  };

  const getFlagColor = (flag: string) => {
    switch(flag) {
      case 'High': return 'text-red-600 bg-red-50';
      case 'Low': return 'text-orange-600 bg-orange-50';
      default: return 'text-green-600 bg-green-50';
    }
  };

  const getFlagIcon = (flag: string) => {
    if (flag === 'High') return '↑';
    if (flag === 'Low') return '↓';
    return '✓';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!document) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Document not found</p>
        <button onClick={() => router.back()} className="mt-4 text-blue-600">Go Back</button>
      </div>
    );
  }

  const isCBC = document.report_type === 'cbc';
  const results: CBCResult[] = editedData?.results || [];

  return (
    <div className="h-screen bg-gray-100 overflow-hidden">
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 px-6 py-4 flex-shrink-0">
          <div className="flex items-center justify-between">
            <div>
              <button onClick={() => router.back()} className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-2">
                <ArrowLeft className="w-4 h-4" />
                Back to Pending
              </button>
              <h1 className="text-xl font-semibold text-gray-900">Review Medical Document</h1>
              <p className="text-sm text-gray-500 mt-1">
                Patient ID: {document.patient_id} | Type: {document.report_type.toUpperCase()} | 
                Uploaded: {new Date(document.created_at).toLocaleString()}
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
                disabled={approving}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center gap-2 disabled:opacity-50"
              >
                {approving ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                ) : (
                  <Check className="w-4 h-4" />
                )}
                {approving ? 'Approving...' : 'Approve & Save'}
              </button>
            </div>
          </div>
        </div>

        {/* Split Screen Content */}
        <div className="flex-1 flex overflow-hidden p-4 gap-4">
          {/* Left Panel - Original Document Viewer */}
          <div className="w-1/2 bg-white rounded-xl border border-gray-200 flex flex-col overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
              <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                <FileText className="w-4 h-4" />
                Original Document
              </h2>
              <p className="text-xs text-gray-500 mt-1">Reference document for validation</p>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              {originalFileUrl ? (
                <div className="text-center">
                  {document.report_type === 'cbc' ? (
                    <img 
                      src={originalFileUrl} 
                      alt="Document preview" 
                      className="max-w-full rounded-lg shadow-sm"
                    />
                  ) : (
                    <iframe 
                      src={originalFileUrl} 
                      className="w-full h-[calc(100vh-250px)] rounded-lg"
                      title="Document preview"
                    />
                  )}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-center text-gray-500">
                  <FileText className="w-16 h-16 mb-4 text-gray-300" />
                  <p>Original document preview not available</p>
                  <p className="text-sm mt-2">The document has been processed but the original file cannot be displayed</p>
                </div>
              )}
            </div>
          </div>

          {/* Right Panel - Editable Extracted Data */}
          <div className="w-1/2 bg-white rounded-xl border border-gray-200 flex flex-col overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
              <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                <Edit2 className="w-4 h-4" />
                AI-Extracted Data (Editable)
              </h2>
              <p className="text-xs text-gray-500 mt-1">Review and correct the extracted information</p>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              {isCBC && results.length > 0 ? (
                <div>
                  {/* Patient Info */}
                  <div className="grid grid-cols-2 gap-4 mb-6 p-4 bg-gray-50 rounded-lg">
                    <div>
                      <label className="text-xs text-gray-500 block">Patient Name</label>
                      <p className="font-medium text-gray-900">{editedData?.patient_name || 'N/A'}</p>
                    </div>
                    <div>
                      <label className="text-xs text-gray-500 block">Collection Date</label>
                      <p className="font-medium text-gray-900">{editedData?.collection_date || 'N/A'}</p>
                    </div>
                  </div>

                  {/* Results Table */}
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50">
                        <tr className="border-b">
                          <th className="text-left p-3 font-medium text-gray-700">Test Name</th>
                          <th className="text-left p-3 font-medium text-gray-700">Value</th>
                          <th className="text-left p-3 font-medium text-gray-700">Unit</th>
                          <th className="text-left p-3 font-medium text-gray-700">Reference Range</th>
                          <th className="text-left p-3 font-medium text-gray-700">Status</th>
                          <th className="w-10"></th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {results.map((result: CBCResult, idx: number) => (
                          <tr key={idx} className={`hover:bg-gray-50 ${result.flag !== 'Normal' ? 'bg-red-50/30' : ''}`}>
                            <td className="p-3 font-medium text-gray-900">{result.test_name}</td>
                            <td className="p-3">
                              {editingCell?.row === idx && editingCell?.field === 'value' ? (
                                <div className="flex items-center gap-2">
                                  <input
                                    type="number"
                                    value={editValue}
                                    onChange={(e) => setEditValue(e.target.value)}
                                    className="w-24 px-2 py-1 border rounded text-sm"
                                    autoFocus
                                  />
                                  <button onClick={() => handleSaveEdit(idx, 'value')} className="text-green-600 hover:text-green-700">
                                    <Check className="w-4 h-4" />
                                  </button>
                                  <button onClick={() => setEditingCell(null)} className="text-gray-400 hover:text-gray-500">
                                    <X className="w-4 h-4" />
                                  </button>
                                </div>
                              ) : (
                                <div 
                                  className={`cursor-pointer hover:bg-gray-100 px-2 py-1 rounded ${result.flag === 'High' ? 'text-red-600 font-semibold' : result.flag === 'Low' ? 'text-orange-600 font-semibold' : ''}`}
                                  onClick={() => handleEdit(idx, 'value', result.value)}
                                >
                                  {result.value}
                                </div>
                              )}
                            </td>
                            <td className="p-3 text-gray-600">{result.unit}</td>
                            <td className="p-3 text-gray-600">
                              {result.reference_range_min} - {result.reference_range_max}
                            </td>
                            <td className="p-3">
                              <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${getFlagColor(result.flag)}`}>
                                <span>{getFlagIcon(result.flag)}</span>
                                {result.flag}
                              </span>
                            </td>
                            <td>
                              <button onClick={() => handleEdit(idx, 'value', result.value)} className="text-gray-400 hover:text-blue-600">
                                <Edit2 className="w-3 h-3" />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Summary Card */}
                  <div className="mt-6 p-4 bg-blue-50 rounded-lg">
                    <h4 className="text-sm font-semibold text-blue-900 mb-2">Clinical Summary</h4>
                    <div className="flex gap-4 text-sm">
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                        <span>Normal: {results.filter(r => r.flag === 'Normal').length}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                        <span>High: {results.filter(r => r.flag === 'High').length}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 bg-orange-500 rounded-full"></div>
                        <span>Low: {results.filter(r => r.flag === 'Low').length}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-center text-gray-500">
                  <AlertCircle className="w-12 h-12 mb-4 text-gray-300" />
                  <p>No structured data available for this document type</p>
                  <p className="text-sm mt-2">The extracted data will appear here for review</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
