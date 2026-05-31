'use client';

import { useState, useEffect, useRef } from 'react';
import { 
  Users, FileText, MessageSquare, Search, ChevronLeft, ChevronRight,
  Stethoscope, Pill, Brain, Activity, Calendar, Phone, 
  Mail, Droplet, AlertCircle, Clock, 
  X, Send, Plus, Trash2, Save, Menu, Sparkles, Copy, Check,
  TrendingUp, TrendingDown, Minus, FileSearch, Database, Zap,
  Bot, UserCircle, Heart, Thermometer, Microscope, ClipboardList,
  Mic, MicOff, Loader2
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { useReactMediaRecorder } from 'react-media-recorder';

interface Patient {
  patient_id: string;
  full_name: string;
  date_of_birth: string;
  gender: string;
  phone?: string;
  email?: string;
  blood_type?: string;
  allergies?: string;
  recent_documents: number;
  last_visit: string;
}

interface Document {
  document_id: string;
  report_type: string;
  data: any;
  created_at: string;
  approval_status?: string;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
}

interface Source {
  source_id: number;
  document_id: string;
  report_type: string;
  page?: number;
  score: number;
}

interface Medication {
  id: string;
  name: string;
  dosage: string;
  timing: string[];
  foodInstruction: string;
  duration: string;
}

export default function DoctorDashboard() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [showDocumentModal, setShowDocumentModal] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const [showSidebar, setShowSidebar] = useState(true);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const [instructions, setInstructions] = useState('');
  const [medications, setMedications] = useState<Medication[]>([
    { id: '1', name: '', dosage: '', timing: [], foodInstruction: 'before', duration: '' }
  ]);
  const [isSaving, setIsSaving] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);

  const [isTranscribing, setIsTranscribing] = useState(false);

  const { status: dictationStatus, startRecording: startDictation, stopRecording: stopDictation } = useReactMediaRecorder({ 
    audio: true,
    onStop: async (blobUrl, blob) => {
      setIsTranscribing(true);
      try {
        const token = localStorage.getItem('access_token');
        const formData = new FormData();
        formData.append('audio', blob, 'dictation.webm');

        const response = await fetch('http://127.0.0.1:8000/doctor/transcribe', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` },
          body: formData
        });

        if (response.ok) {
          const data = await response.json();
          // Appends the new text to whatever the doctor already typed!
          setInstructions(prev => prev + (prev ? " " : "") + data.transcription);
        } else {
            console.error("Transcription API returned an error.");
        }
      } catch (error) {
        console.error("Dictation failed:", error);
      } finally {
        setIsTranscribing(false);
      }
    }
  });
  useEffect(() => {
    const fetchPatients = async () => {
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch('http://127.0.0.1:8000/doctor/my-patients', {
          headers: { 'Authorization': `Bearer ${token}` },
        });
        if (response.ok) {
          const data = await response.json();
          setPatients(data.patients || []);
        }
      } catch (error) {
        console.error('Error fetching patients:', error);
      }
    };
    fetchPatients();
  }, []);

  const fetchPatientDocuments = async (patientId: string) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`http://127.0.0.1:8000/doctor/patient/${patientId}/full-history`, {
        headers: { 'Authorization': `Bearer ${token}` },
      }); 
      if (response.ok) {
        const data = await response.json();
        setDocuments(data.documents || []);
      }
    } catch (error) {
      console.error('Failed to fetch documents:', error);
    }
  };

  const handleSelectPatient = async (patient: Patient) => {
    setSelectedPatient(patient);
    await fetchPatientDocuments(patient.patient_id);
    setMessages([]);
    setActiveTab('overview');
    setShowSidebar(false);
    setInstructions('');
    setMedications([{ id: '1', name: '', dosage: '', timing: [], foodInstruction: 'before', duration: '' }]);
  };

  const toggleSidebar = () => {
    setShowSidebar(!showSidebar);
  };

  const handleSendMessage = async () => {
    if (!input.trim() || !selectedPatient) return;

    const userMessage: ChatMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('http://127.0.0.1:8000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ 
          query: input, 
          history: messages.map(m => ({ role: m.role, content: m.content })),
          patient_id: selectedPatient.patient_id
        }),
      });
      
      if (response.ok) {
        const data = await response.json();
        const assistantMessage: ChatMessage = {
          role: 'assistant',
          content: data.final_answer,
          sources: data.sources || [],
        };
        setMessages(prev => [...prev, assistantMessage]);
      } else {
        setMessages(prev => [...prev, { 
          role: 'assistant', 
          content: 'Sorry, I could not process your request.' 
        }]);
      }
    } catch (error) {
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Error connecting to AI service.' 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleCitationClick = (source: Source) => {
    const doc = documents.find(d => d.document_id === source.document_id);
    if (doc) {
      setSelectedDocument(doc);
      setShowDocumentModal(true);
    }
  };

  const copyToClipboard = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const addMedication = () => {
    setMedications([
      ...medications,
      { id: Date.now().toString(), name: '', dosage: '', timing: [], foodInstruction: 'before', duration: '' }
    ]);
  };

  const removeMedication = (id: string) => {
    if (medications.length === 1) return;
    setMedications(medications.filter(m => m.id !== id));
  };

  const updateMedication = (id: string, field: string, value: any) => {
    setMedications(medications.map(m => 
      m.id === id ? { ...m, [field]: value } : m
    ));
  };

  const toggleTiming = (id: string, timing: string) => {
    setMedications(medications.map(m => {
      if (m.id === id) {
        const timings = m.timing.includes(timing)
          ? m.timing.filter(t => t !== timing)
          : [...m.timing, timing];
        return { ...m, timing: timings };
      }
      return m;
    }));
  };

  const handleSavePrescription = async () => {
    if (!selectedPatient) return;
    
    setIsSaving(true);
    try {
      const token = localStorage.getItem('access_token');
      const user = JSON.parse(localStorage.getItem('user') || '{}');
      const payload = {
        patient_id: selectedPatient.patient_id,
        doctor_id: user.id,
        instructions: instructions,
        medications: medications.filter(m => m.name.trim()).map(m => ({
          medicine_name: m.name,
          dosage: m.dosage,
          timing: m.timing[0] || 'morning',
          food_instruction: m.foodInstruction,
          frequency: 'daily'
        }))
      };

      const response = await fetch('http://127.0.0.1:8000/prescriptions/direct', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        alert('Prescription saved successfully!');
        await fetchPatientDocuments(selectedPatient.patient_id);
        setActiveTab('prescriptions');
        setInstructions('');
        setMedications([{ id: '1', name: '', dosage: '', timing: [], foodInstruction: 'before', duration: '' }]);
      } else {
        const error = await response.json();
        alert('Failed to save prescription: ' + error.detail);
      }
    } catch (error) {
      console.error('Error saving prescription:', error);
      alert('Failed to save prescription');
    } finally {
      setIsSaving(false);
    }
  };

  const calculateAge = (dob: string) => {
    if (!dob) return 'N/A';
    const birthDate = new Date(dob);
    const diff = new Date().getTime() - birthDate.getTime();
    const age = Math.floor(diff / (1000 * 60 * 60 * 24 * 365.25));
    return `${age}`;
  };

  const formatDate = (date: string) => {
    if (!date) return 'N/A';
    return new Date(date).toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric' 
    });
  };

  const filteredPatients = patients.filter(p => 
    p.full_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    p.patient_id?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const reports = documents.filter(d => d.report_type === 'cbc');
  const prescriptions = documents.filter(d => d.report_type === 'digital_prescription');
  const timingOptions = ['Morning', 'Afternoon', 'Evening', 'Night'];
  const foodOptions = ['Before Food', 'After Food', 'With Food', 'Independent'];

  return (
    <div className="h-screen bg-gradient-to-br from-gray-50 to-gray-100 overflow-hidden">
      <div className="flex h-full">
        {/* Sidebar */}
        <div className={`${showSidebar ? 'w-80' : 'w-0'} bg-white/80 backdrop-blur-sm border-r border-gray-200 flex flex-col transition-all duration-300 overflow-hidden flex-shrink-0 shadow-xl z-10`}>
          <div className="p-5 border-b border-gray-100">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-blue-600 rounded-xl flex items-center justify-center shadow-md">
                  <Activity className="w-4 h-4 text-white" />
                </div>
                <h2 className="text-lg font-semibold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">My Patients</h2>
              </div>
              <span className="text-xs bg-blue-100 text-blue-700 px-2.5 py-1 rounded-full font-medium">{patients.length}</span>
            </div>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search by name or MRN..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 text-sm border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-gray-50/50"
              />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-2">
            {filteredPatients.length === 0 ? (
              <div className="p-8 text-center">
                <Users className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                <p className="text-sm text-gray-500">No patients assigned</p>
              </div>
            ) : (
              filteredPatients.map((patient) => (
                <div
                  key={patient.patient_id}
                  onClick={() => handleSelectPatient(patient)}
                  className={`px-4 py-3 mx-1 rounded-xl cursor-pointer transition-all duration-200 ${
                    selectedPatient?.patient_id === patient.patient_id 
                      ? 'bg-gradient-to-r from-blue-50 to-blue-100 border-l-4 border-l-blue-500 shadow-sm' 
                      : 'hover:bg-gray-50'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-blue-400 to-blue-600 rounded-xl flex items-center justify-center text-white font-semibold text-sm shadow-md">
                      {patient.full_name?.charAt(0)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-gray-900 truncate">{patient.full_name}</p>
                      <p className="text-xs text-gray-500 mt-0.5">MRN: {patient.patient_id}</p>
                      <div className="flex items-center gap-2 mt-1 text-xs text-gray-400">
                        <span>{calculateAge(patient.date_of_birth)} yrs</span>
                        <span>•</span>
                        <span className="capitalize">{patient.gender}</span>
                      </div>
                    </div>
                    {patient.recent_documents > 0 && (
                      <div className="flex items-center gap-1 text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full">
                        <FileText className="w-3 h-3" />
                        <span>{patient.recent_documents}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Header */}
          <div className="bg-white/80 backdrop-blur-sm border-b border-gray-100 px-6 py-4 flex-shrink-0 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <button
                  onClick={toggleSidebar}
                  className="p-2 hover:bg-gray-100 rounded-xl transition-all duration-200"
                  title={showSidebar ? "Hide patient list" : "Show patient list"}
                >
                  {showSidebar ? <ChevronLeft className="w-5 h-5 text-gray-500" /> : <ChevronRight className="w-5 h-5 text-gray-500" />}
                </button>
                
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 bg-gradient-to-r from-blue-500 to-blue-600 rounded-xl flex items-center justify-center shadow-md">
                    <Activity className="w-5 h-5 text-white" />
                  </div>
                  <span className="text-xl font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">MedFlow AI</span>
                </div>
                
                {selectedPatient && (
                  <div className="flex items-center gap-3 ml-4 pl-4 border-l border-gray-200">
                    <div className="w-10 h-10 bg-gradient-to-br from-emerald-400 to-teal-500 rounded-xl flex items-center justify-center text-white font-bold shadow-md">
                      {selectedPatient.full_name?.charAt(0)}
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900">{selectedPatient.full_name}</p>
                      <p className="text-xs text-gray-500">MRN: {selectedPatient.patient_id}</p>
                    </div>
                  </div>
                )}
              </div>
              
              {selectedPatient && (
                <div className="flex items-center gap-4 text-xs text-gray-500">
                  <span className="flex items-center gap-1.5"><Phone className="w-3.5 h-3.5" /> {selectedPatient.phone || 'Not provided'}</span>
                  <span className="flex items-center gap-1.5"><Mail className="w-3.5 h-3.5" /> {selectedPatient.email || 'Not provided'}</span>
                  <span className="flex items-center gap-1.5"><Droplet className="w-3.5 h-3.5" /> {selectedPatient.blood_type || 'Unknown'}</span>
                </div>
              )}
            </div>
          </div>

          {!selectedPatient ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <div className="w-24 h-24 bg-gradient-to-br from-blue-100 to-purple-100 rounded-3xl flex items-center justify-center mx-auto mb-5 shadow-lg">
                  <Stethoscope className="w-12 h-12 text-blue-500" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">Select a Patient</h3>
                <p className="text-gray-500">Click the sidebar button and select a patient to view their clinical information</p>
              </div>
            </div>
          ) : (
            <>
              {/* Tabs */}
              <div className="bg-white/80 backdrop-blur-sm border-b border-gray-100 px-6 flex-shrink-0">
                <div className="flex gap-1">
                  {[
                    { id: 'overview', label: 'Overview', icon: <Activity className="w-4 h-4" /> },
                    { id: 'reports', label: 'Reports', icon: <FileText className="w-4 h-4" /> },
                    { id: 'prescriptions', label: 'Prescriptions', icon: <Pill className="w-4 h-4" /> },
                    { id: 'new-prescription', label: 'Write Rx', icon: <Plus className="w-4 h-4" /> },
                    { id: 'chat', label: 'AI Chat', icon: <Brain className="w-4 h-4" /> }
                  ].map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`flex items-center gap-2 px-5 py-3 text-sm font-medium transition-all duration-200 rounded-t-xl ${
                        activeTab === tab.id 
                          ? 'bg-white text-blue-600 border-b-2 border-blue-500 shadow-sm' 
                          : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                      }`}
                    >
                      {tab.icon}
                      {tab.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Content Area */}
              <div className="flex-1 overflow-y-auto p-6">
                {activeTab === 'overview' && (
                  <div className="space-y-4">
                    <div className="flex items-center gap-2 mb-4">
                      <ClipboardList className="w-5 h-5 text-blue-500" />
                      <h3 className="text-lg font-semibold text-gray-900">Recent Medical Records</h3>
                    </div>
                    {documents.length === 0 ? (
                      <div className="text-center py-12 bg-white rounded-2xl border">
                        <FileText className="w-16 h-16 text-gray-300 mx-auto mb-3" />
                        <p className="text-gray-500">No medical records found</p>
                      </div>
                    ) : (
                      <div className="grid gap-4">
                        {documents.slice(0, 10).map((doc) => (
                          <div key={doc.document_id} className="bg-white rounded-xl border border-gray-100 p-5 hover:shadow-md transition-all cursor-pointer group">
                            <div className="flex justify-between items-start mb-3">
                              <div className="flex items-center gap-2">
                                <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                                  <FileText className="w-4 h-4 text-blue-600" />
                                </div>
                                <span className="font-semibold text-gray-800 capitalize">{doc.report_type?.replace('_', ' ')}</span>
                              </div>
                              <span className="text-xs text-gray-400">{formatDate(doc.created_at)}</span>
                            </div>
                            <button 
                              onClick={() => {
                                setSelectedDocument(doc);
                                setShowDocumentModal(true);
                              }}
                              className="text-blue-600 text-sm hover:underline flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
                            >
                              View Details →
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {activeTab === 'reports' && (
                  <div className="space-y-4">
                    <div className="flex items-center gap-2 mb-4">
                      <Microscope className="w-5 h-5 text-blue-500" />
                      <h3 className="text-lg font-semibold text-gray-900">Lab Reports</h3>
                    </div>
                    {reports.length === 0 ? (
                      <div className="text-center py-12 bg-white rounded-2xl border">
                        <FileText className="w-16 h-16 text-gray-300 mx-auto mb-3" />
                        <p className="text-gray-500">No lab reports found</p>
                      </div>
                    ) : (
                      reports.map((doc) => (
                        <div key={doc.document_id} className="bg-white rounded-xl border border-gray-100 p-5 hover:shadow-md transition-all">
                          <div className="flex justify-between items-center mb-4">
                            <div className="flex items-center gap-2">
                              <div className="w-8 h-8 bg-emerald-100 rounded-lg flex items-center justify-center">
                                <Activity className="w-4 h-4 text-emerald-600" />
                              </div>
                              <span className="font-semibold text-gray-800">CBC Report</span>
                            </div>
                            <span className="text-xs text-gray-400">{formatDate(doc.created_at)}</span>
                          </div>
                          {doc.data?.results && (
                            <div className="grid grid-cols-2 gap-3 text-sm mb-4 bg-gray-50 rounded-lg p-3">
                              {doc.data.results.slice(0, 8).map((result: any, idx: number) => (
                                <div key={idx} className="flex justify-between items-center py-1">
                                  <span className="text-gray-600">{result.test_name}:</span>
                                  <span className={`font-medium ${result.flag === 'High' ? 'text-red-600' : result.flag === 'Low' ? 'text-orange-600' : 'text-gray-800'}`}>
                                    {result.value} {result.unit}
                                  </span>
                                </div>
                              ))}
                            </div>
                          )}
                          <button 
                            onClick={() => {
                              setSelectedDocument(doc);
                              setShowDocumentModal(true);
                            }}
                            className="text-blue-600 text-sm hover:underline flex items-center gap-1"
                          >
                            View Full Report →
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                )}

                {activeTab === 'prescriptions' && (
                  <div className="space-y-4">
                    <div className="flex items-center gap-2 mb-4">
                      <Pill className="w-5 h-5 text-blue-500" />
                      <h3 className="text-lg font-semibold text-gray-900">Previous Prescriptions</h3>
                    </div>
                    {prescriptions.length === 0 ? (
                      <div className="text-center py-12 bg-white rounded-2xl border">
                        <Pill className="w-16 h-16 text-gray-300 mx-auto mb-3" />
                        <p className="text-gray-500">No previous prescriptions found</p>
                      </div>
                    ) : (
                      prescriptions.map((doc) => (
                        <div key={doc.document_id} className="bg-white rounded-xl border border-gray-100 p-5 hover:shadow-md transition-all">
                          <div className="flex justify-between items-center mb-4">
                            <div className="flex items-center gap-2">
                              <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center">
                                <Pill className="w-4 h-4 text-purple-600" />
                              </div>
                              <span className="font-semibold text-gray-800">Prescription</span>
                            </div>
                            <span className="text-xs text-gray-400">{formatDate(doc.created_at)}</span>
                          </div>
                          {doc.data?.medications && (
                            <div className="space-y-2 bg-gray-50 rounded-lg p-3">
                              {doc.data.medications.map((med: any, idx: number) => (
                                <div key={idx} className="flex justify-between items-center py-2 border-b border-gray-200 last:border-0">
                                  <div className="flex items-center gap-2">
                                    <Pill className="w-3 h-3 text-green-500" />
                                    <span className="font-medium text-gray-800">{med.medicine_name}</span>
                                  </div>
                                  <span className="text-sm text-gray-500">{med.dosage}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                )}

                {activeTab === 'new-prescription' && (
                  <div className="max-w-3xl mx-auto space-y-6">
                    <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm">
                      <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                        <ClipboardList className="w-4 h-4 text-blue-500" />
                        Prescription Instructions (Voice Supported)
                      </label>
                      <div className="relative">
                        <textarea
                          value={instructions}
                          onChange={(e) => setInstructions(e.target.value)}
                          rows={4}
                          placeholder="Type or click the mic to dictate diagnosis, instructions, and notes..."
                          className="w-full px-4 py-3 pr-14 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                        <button
                          onClick={dictationStatus === 'recording' ? stopDictation : startDictation}
                          disabled={isTranscribing}
                          className={`absolute bottom-3 right-3 p-2 rounded-xl transition-all shadow-sm ${
                            dictationStatus === 'recording' 
                              ? 'bg-red-100 text-red-600 animate-pulse ring-2 ring-red-400' 
                              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                          }`}
                          title={dictationStatus === 'recording' ? "Stop dictation" : "Start medical dictation"}
                        >
                          {isTranscribing ? (
                            <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
                          ) : dictationStatus === 'recording' ? (
                            <MicOff className="w-5 h-5" />
                          ) : (
                            <Mic className="w-5 h-5" />
                          )}
                        </button>
                      </div>
                    </div>

                    <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm">
                      <div className="flex justify-between items-center mb-4">
                        <div className="flex items-center gap-2">
                          <Pill className="w-5 h-5 text-blue-500" />
                          <h3 className="font-semibold text-gray-900">Medications</h3>
                        </div>
                        <button
                          onClick={addMedication}
                          className="px-3 py-1.5 text-sm bg-blue-50 text-blue-600 rounded-xl hover:bg-blue-100 flex items-center gap-1 transition-all"
                        >
                          <Plus className="w-4 h-4" />
                          Add Medicine
                        </button>
                      </div>

                      <div className="space-y-4">
                        {medications.map((med, idx) => (
                          <div key={med.id} className="border border-gray-200 rounded-xl p-4 hover:border-blue-200 transition-all">
                            <div className="flex justify-between items-start mb-3">
                              <span className="text-sm font-medium text-gray-500">Medication #{idx + 1}</span>
                              {medications.length > 1 && (
                                <button onClick={() => removeMedication(med.id)} className="text-red-400 hover:text-red-600">
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              )}
                            </div>
                            <div className="grid grid-cols-2 gap-4 mb-4">
                              <div>
                                <label className="text-xs text-gray-500 mb-1 block">Medicine Name & Dose</label>
                                <input
                                  type="text"
                                  value={med.name}
                                  onChange={(e) => updateMedication(med.id, 'name', e.target.value)}
                                  placeholder="e.g., Paracetamol 650mg"
                                  className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500"
                                />
                              </div>
                              <div>
                                <label className="text-xs text-gray-500 mb-1 block">Duration</label>
                                <input
                                  type="text"
                                  value={med.duration}
                                  onChange={(e) => updateMedication(med.id, 'duration', e.target.value)}
                                  placeholder="e.g., 7 days"
                                  className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg"
                                />
                              </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                              <div>
                                <label className="text-xs text-gray-500 mb-2 block">Timing</label>
                                <div className="flex flex-wrap gap-3">
                                  {timingOptions.map((t) => (
                                    <label key={t} className="flex items-center gap-1.5">
                                      <input
                                        type="checkbox"
                                        checked={med.timing.includes(t)}
                                        onChange={() => toggleTiming(med.id, t)}
                                        className="w-4 h-4 text-blue-600 rounded"
                                      />
                                      <span className="text-sm text-gray-600">{t}</span>
                                    </label>
                                  ))}
                                </div>
                              </div>
                              <div>
                                <label className="text-xs text-gray-500 mb-2 block">With Food</label>
                                <div className="flex flex-wrap gap-3">
                                  {foodOptions.map((f) => (
                                    <label key={f} className="flex items-center gap-1.5">
                                      <input
                                        type="radio"
                                        name={`food-${med.id}`}
                                        checked={med.foodInstruction === f.toLowerCase().replace(' ', '_')}
                                        onChange={() => updateMedication(med.id, 'foodInstruction', f.toLowerCase().replace(' ', '_'))}
                                        className="w-4 h-4 text-blue-600"
                                      />
                                      <span className="text-sm text-gray-600">{f}</span>
                                    </label>
                                  ))}
                                </div>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>

                      <div className="flex justify-end mt-6 pt-4 border-t border-gray-100">
                        <button
                          onClick={handleSavePrescription}
                          disabled={isSaving}
                          className="px-6 py-2.5 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-xl hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 transition-all shadow-md"
                        >
                          {isSaving ? 'Saving...' : 'Save Prescription'}
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {activeTab === 'chat' && (
                  <div className="flex flex-col h-[calc(100vh-200px)]">
                    <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-2">
                      {messages.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-full text-center">
                          <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center mb-5 shadow-lg">
                            <Brain className="w-10 h-10 text-white" />
                          </div>
                          <h3 className="text-xl font-semibold text-gray-900 mb-2">AI Clinical Assistant</h3>
                          <p className="text-gray-500 max-w-md mb-6">
                            Ask me anything about {selectedPatient.full_name}'s medical history, lab results, or medications.
                          </p>
                          <div className="flex flex-wrap gap-3 justify-center">
                            {[
                              { icon: <Activity className="w-4 h-4" />, text: "What are the latest lab results?" },
                              { icon: <Pill className="w-4 h-4" />, text: "Show current medications" },
                              { icon: <AlertCircle className="w-4 h-4" />, text: "Any abnormal findings?" },
                              { icon: <FileText className="w-4 h-4" />, text: "Summarize health records" }
                            ].map((suggestion, idx) => (
                              <button
                                key={idx}
                                onClick={() => {
                                  setInput(suggestion.text);
                                  setTimeout(() => handleSendMessage(), 100);
                                }}
                                className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-full text-sm text-gray-700 hover:border-blue-400 hover:bg-blue-50 transition-all shadow-sm"
                              >
                                {suggestion.icon}
                                {suggestion.text}
                              </button>
                            ))}
                          </div>
                        </div>
                      ) : (
                        messages.map((msg, idx) => (
                          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                            <div className={`max-w-[80%] ${msg.role === 'user' ? 'bg-gradient-to-r from-blue-600 to-blue-700 text-white' : 'bg-white border border-gray-200'} rounded-2xl shadow-sm overflow-hidden`}>
                              <div className={`px-4 py-2.5 border-b flex items-center justify-between ${msg.role === 'user' ? 'border-blue-500' : 'border-gray-100'}`}>
                                <div className="flex items-center gap-2">
                                  {msg.role === 'user' ? (
                                    <>
                                      <div className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
                                        <UserCircle className="w-4 h-4 text-white" />
                                      </div>
                                      <span className="text-sm font-medium">Doctor</span>
                                    </>
                                  ) : (
                                    <>
                                      <div className="w-6 h-6 bg-gradient-to-r from-purple-500 to-blue-500 rounded-full flex items-center justify-center">
                                        <Bot className="w-3 h-3 text-white" />
                                      </div>
                                      <span className="text-sm font-medium text-gray-900">AI Clinical Assistant</span>
                                      <span className="text-xs text-gray-400 ml-2">Powered by GPT-4</span>
                                    </>
                                  )}
                                </div>
                                {msg.role === 'assistant' && (
                                  <button
                                    onClick={() => copyToClipboard(msg.content, idx)}
                                    className="text-gray-400 hover:text-gray-600 transition"
                                  >
                                    {copiedIndex === idx ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
                                  </button>
                                )}
                              </div>

                              <div className="px-4 py-3">
                                {msg.role === 'assistant' ? (
                                  <div className="prose prose-sm max-w-none">
                                    <ReactMarkdown
                                      remarkPlugins={[remarkGfm]}
                                      rehypePlugins={[rehypeRaw]}
                                      components={{
                                        h1: ({node, ...props}) => <h1 className="text-lg font-bold mt-4 mb-2 text-gray-900" {...props} />,
                                        h2: ({node, ...props}) => <h2 className="text-md font-semibold mt-3 mb-2 text-gray-900" {...props} />,
                                        h3: ({node, ...props}) => <h3 className="text-sm font-semibold mt-2 mb-1 text-gray-800" {...props} />,
                                        p: ({node, ...props}) => <p className="text-sm text-gray-700 mb-2 leading-relaxed" {...props} />,
                                        ul: ({node, ...props}) => <ul className="list-disc list-inside mb-2 space-y-1" {...props} />,
                                        ol: ({node, ...props}) => <ol className="list-decimal list-inside mb-2 space-y-1" {...props} />,
                                        li: ({node, ...props}) => <li className="text-sm text-gray-700" {...props} />,
                                        strong: ({node, ...props}) => <strong className="font-semibold text-gray-900" {...props} />,
                                        code: ({node, ...props}) => <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs font-mono" {...props} />,
                                        pre: ({node, ...props}) => <pre className="bg-gray-100 p-3 rounded-lg overflow-x-auto text-xs" {...props} />,
                                      }}
                                    >
                                      {msg.content}
                                    </ReactMarkdown>
                                  </div>
                                ) : (
                                  <p className="text-sm">{msg.content}</p>
                                )}

                                {msg.sources && msg.sources.length > 0 && (
                                  <div className="mt-3 pt-2 border-t border-gray-100">
                                    <div className="flex items-center gap-1.5 mb-2">
                                      <Database className="w-3.5 h-3.5 text-gray-400" />
                                      <span className="text-xs font-medium text-gray-500">Sources</span>
                                      <span className="text-xs text-gray-400">({msg.sources.length})</span>
                                    </div>
                                    <div className="flex flex-wrap gap-2">
                                      {msg.sources.map((source, sidx) => (
                                        <button
                                          key={sidx}
                                          onClick={() => handleCitationClick(source)}
                                          className="flex items-center gap-1.5 px-2.5 py-1.5 bg-gray-100 hover:bg-blue-100 rounded-lg text-xs text-gray-600 hover:text-blue-700 transition-all"
                                        >
                                          <FileSearch className="w-3 h-3" />
                                          {source.report_type?.replace('_', ' ')} 
                                          <span className="text-gray-400">•</span>
                                          <span className="font-medium">{Math.round(source.score * 100)}%</span>
                                          <Zap className="w-2.5 h-2.5 text-amber-500" />
                                        </button>
                                      ))}
                                    </div>
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        ))
                      )}
                      
                      {isLoading && (
                        <div className="flex justify-start">
                          <div className="bg-white border border-gray-200 rounded-2xl p-4 shadow-sm">
                            <div className="flex items-center gap-3">
                              <div className="w-8 h-8 bg-gradient-to-r from-purple-500 to-blue-500 rounded-full flex items-center justify-center">
                                <Brain className="w-4 h-4 text-white" />
                              </div>
                              <div className="flex gap-1.5">
                                <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                                <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                                <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                              </div>
                              <span className="text-sm text-gray-500 ml-2">Analyzing medical records...</span>
                            </div>
                          </div>
                        </div>
                      )}
                      <div ref={chatEndRef} />
                    </div>

                    {/* Input Area */}
                    <div className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm">
                      <div className="flex gap-3">
                        <div className="flex-1 relative">
                          <textarea
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyPress={handleKeyPress}
                            placeholder="Ask about patient's medical history, lab results, or medications..."
                            rows={1}
                            className="w-full px-4 py-3 pr-12 text-sm border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                            style={{ minHeight: '48px', maxHeight: '120px' }}
                            onInput={(e) => {
                              const target = e.target as HTMLTextAreaElement;
                              target.style.height = 'auto';
                              target.style.height = Math.min(target.scrollHeight, 120) + 'px';
                            }}
                          />
                          <div className="absolute right-3 bottom-3 flex items-center gap-1">
                            <div className="text-xs text-gray-400">
                              {input.length > 0 && <span className="mr-1">↵ Send</span>}
                            </div>
                          </div>
                        </div>
                        <button
                          onClick={handleSendMessage}
                          disabled={isLoading || !input.trim()}
                          className="px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-xl hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 transition-all flex items-center gap-2 shadow-md"
                        >
                          <Send className="w-4 h-4" />
                          Send
                        </button>
                      </div>
                      <div className="flex items-center justify-between mt-3 text-xs text-gray-400">
                        <div className="flex items-center gap-2">
                          <Sparkles className="w-3.5 h-3.5" />
                          <span>AI responses are based on patient's medical records using RAG</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></div>
                          <span>HIPAA Compliant • Secure</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Document Viewer Modal */}
      {showDocumentModal && selectedDocument && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[80vh] flex flex-col animate-in zoom-in-95 duration-200">
            <div className="flex justify-between items-center p-5 border-b">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
                  <FileText className="w-4 h-4 text-white" />
                </div>
                <h3 className="font-semibold text-lg capitalize">{selectedDocument.report_type?.replace('_', ' ')}</h3>
                <span className="text-sm text-gray-400 ml-2">{formatDate(selectedDocument.created_at)}</span>
              </div>
              <button onClick={() => setShowDocumentModal(false)} className="p-2 hover:bg-gray-100 rounded-xl transition">
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-6">
              <pre className="text-sm bg-gray-50 p-5 rounded-xl overflow-auto">
                {JSON.stringify(selectedDocument.data, null, 2)}
              </pre>
            </div>
            <div className="p-5 border-t flex justify-end">
              <button onClick={() => setShowDocumentModal(false)} className="px-5 py-2 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 transition">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
