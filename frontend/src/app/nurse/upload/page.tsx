'use client';

import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, File, X, CheckCircle, AlertCircle, Loader2, FileText, Image } from 'lucide-react';

const reportTypes = [
  { value: 'cbc', label: 'CBC Report' },
  { value: 'digital_prescription', label: 'Prescription' },
  { value: 'discharge_summary', label: 'Discharge Summary' },
  { value: 'medical_invoice', label: 'Medical Invoice' },
];

type UploadStatus = 'uploading' | 'success' | 'error';

interface FileUpload {
  file: File;
  preview: string;
  patientId: string;
  reportType: string;
  status: UploadStatus;
  progress: number;
  documentId?: string;
  error?: string;
}

export default function NurseUploadPage() {
  const [uploads, setUploads] = useState<FileUpload[]>([]);
  const [selectedPatient, setSelectedPatient] = useState('');
  const [selectedReportType, setSelectedReportType] = useState('cbc');

  const uploadDocument = async (file: File, patientId: string, reportType: string) => {
    const token = localStorage.getItem('access_token');
    const formData = new FormData();
    formData.append('file', file);
    formData.append('patient_id', patientId);
    formData.append('report_type', reportType);

    const response = await fetch('http://localhost:8000/upload', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || error.error || 'Upload failed');
    }
    return response.json();
  };

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newUploads: FileUpload[] = acceptedFiles.map((file) => ({
      file,
      preview: URL.createObjectURL(file),
      patientId: selectedPatient,
      reportType: selectedReportType,
      status: 'uploading',
      progress: 0,
    }));
    setUploads(prev => [...prev, ...newUploads]);
    newUploads.forEach(upload => handleUpload(upload));
  }, [selectedPatient, selectedReportType]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
    },
  });

  const handleUpload = async (upload: FileUpload) => {
    if (!upload.patientId) {
      setUploads(prev => prev.map(u => 
        u.file === upload.file ? { ...u, status: 'error', error: 'Patient ID required' } : u
      ));
      return;
    }

    try {
      setUploads(prev => prev.map(u => 
        u.file === upload.file ? { ...u, progress: 50 } : u
      ));
      const result = await uploadDocument(upload.file, upload.patientId, upload.reportType);
      setUploads(prev => prev.map(u => 
        u.file === upload.file ? { ...u, status: 'success', progress: 100, documentId: result.document_id } : u
      ));
    } catch (error) {
      setUploads(prev => prev.map(u => 
        u.file === upload.file ? { ...u, status: 'error', error: error instanceof Error ? error.message : 'Upload failed' } : u
      ));
    }
  };

  const removeUpload = (file: File) => {
    setUploads(prev => prev.filter(u => u.file !== file));
  };

  const getStatusIcon = (status: UploadStatus) => {
    if (status === 'uploading') return <Loader2 className="w-4 h-4 animate-spin text-blue-600" />;
    if (status === 'success') return <CheckCircle className="w-4 h-4 text-green-600" />;
    if (status === 'error') return <AlertCircle className="w-4 h-4 text-red-600" />;
    return <File className="w-4 h-4 text-gray-400" />;
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Upload Documents</h1>
        <p className="text-gray-600">Upload patient reports for AI extraction</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Patient ID / MRN</label>
          <input
            type="text"
            value={selectedPatient}
            onChange={(e) => setSelectedPatient(e.target.value)}
            placeholder="e.g., PN2"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Report Type</label>
          <select
            value={selectedReportType}
            onChange={(e) => setSelectedReportType(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
          >
            {reportTypes.map(type => (
              <option key={type.value} value={type.value}>{type.label}</option>
            ))}
          </select>
        </div>
      </div>

      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition ${
          isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-blue-400'
        }`}
      >
        <input {...getInputProps()} />
        <Upload className="w-10 h-10 mx-auto mb-3 text-gray-400" />
        <p className="text-gray-600">{isDragActive ? 'Drop files here' : 'Drag & drop or click to select'}</p>
        <p className="text-sm text-gray-400 mt-1">PDF, PNG, JPG up to 10MB</p>
      </div>

      {uploads.length > 0 && (
        <div className="mt-6 bg-white rounded-xl border border-gray-200">
          <div className="p-4 border-b border-gray-200">
            <h3 className="font-semibold">Upload Queue ({uploads.length})</h3>
          </div>
          <div className="divide-y divide-gray-200">
            {uploads.map((upload) => (
              <div key={upload.file.name} className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {upload.file.type.includes('pdf') ? (
                    <FileText className="w-8 h-8 text-red-500" />
                  ) : (
                    <Image className="w-8 h-8 text-blue-500" />
                  )}
                  <div>
                    <p className="text-sm font-medium">{upload.file.name}</p>
                    <p className="text-xs text-gray-500">{(upload.file.size / 1024).toFixed(0)} KB</p>
                    {upload.documentId && (
                      <p className="text-xs text-green-600 mt-1">ID: {upload.documentId}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2">
                    {getStatusIcon(upload.status)}
                    <span className="text-sm text-gray-600">
                      {upload.status === 'uploading' && `${upload.progress}%`}
                      {upload.status === 'success' && 'Done'}
                      {upload.status === 'error' && upload.error}
                    </span>
                  </div>
                  {upload.status !== 'success' && (
                    <button onClick={() => removeUpload(upload.file)} className="p-1 hover:bg-gray-100 rounded">
                      <X className="w-4 h-4 text-gray-400" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
