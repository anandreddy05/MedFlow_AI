'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { 
  FileText, MessageSquare, Calendar, Activity, Pill, Heart, 
  Download, ChevronRight, Brain, Send, Mic, MicOff, 
  Sparkles, Database, FileSearch, Zap, Copy, Check,
  AlertCircle, Shield, Loader2
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { useReactMediaRecorder } from 'react-media-recorder';
import { API_BASE_URL } from '@/lib/api/client';

interface Document {
  document_id: string;
  report_type: string;
  data: any;
  date: string;
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
}

export default function PatientDashboard() {
  const router = useRouter();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [patientId, setPatientId] = useState('');
  const [activeTab, setActiveTab] = useState('reports');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchPatientData = async () => {
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`${API_BASE_URL}/patient/history`, {
          headers: { 'Authorization': `Bearer ${token}` },
        });
        if (response.ok) {
          const data = await response.json();
          setPatientId(data.patient_id);
          setDocuments(data.history || []);
        }
      } catch (error) {
        console.error('Failed to fetch patient data:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchPatientData();
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const {
    status,
    startRecording,
    stopRecording,
  } = useReactMediaRecorder({ 
    audio: true,
    onStop: async (blobUrl, blob) => {
      setIsLoading(true);
      try {
        const token = localStorage.getItem('access_token');
        const formData = new FormData();
        formData.append('audio', blob, 'patient_voice.webm');

        const response = await fetch(`${API_BASE_URL}/chat/voice`, {
          method: 'POST',
          headers: { 
            'Authorization': `Bearer ${token}` 
          },
          body: formData
        });

        if (response.ok) {
          const data = await response.json();
          setMessages(prev => [
            ...prev, 
            { role: 'user', content: data.user_transcript },
            { role: 'assistant', content: data.final_answer, sources: data.sources || [] }
          ]);
          if (data.audio_base64) {
            try {
              const audio = new Audio(`data:audio/mp3;base64,${data.audio_base64}`);
              audio.play();
            } catch (audioError) {
              console.error("Failed to play audio:", audioError);
            }
          }
        } else {
          setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I could not process your voice request.' }]);
        }
      } catch (error) {
        console.error("Voice pipeline failed", error);
        setMessages(prev => [...prev, { role: 'assistant', content: 'Error connecting to the voice service.' }]);
      } finally {
        setIsLoading(false);
      }
    }
  });

  const handleStartRecording = () => {
    startRecording();
  };

  const handleStopRecording = () => {
    stopRecording();
  };

  const getReportIcon = (type: string) => {
    switch(type) {
      case 'cbc': return <Activity className="w-4 h-4 text-blue-500" />;
      case 'digital_prescription': return <Pill className="w-4 h-4 text-green-500" />;
      case 'discharge_summary': return <FileText className="w-4 h-4 text-purple-500" />;
      default: return <FileText className="w-4 h-4 text-gray-500" />;
    }
  };

  const getReportTitle = (type: string) => {
    switch(type) {
      case 'cbc': return 'CBC Report';
      case 'digital_prescription': return 'Prescription';
      case 'discharge_summary': return 'Discharge Summary';
      default: return type;
    }
  };

  const handleSendMessage = async () => {
    if (!input.trim()) return;

    const userMessage: ChatMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ 
          query: input, 
          history: messages.map(m => ({ role: m.role, content: m.content }))
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

  const copyToClipboard = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const handleCitationClick = (source: Source) => {
    const doc = documents.find(d => d.document_id === source.document_id);
    if (doc) {
      alert(`Document: ${doc.report_type}\nDate: ${new Date(doc.date).toLocaleDateString()}`);
    }
  };

  const isRecording = status === 'recording';

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gradient-to-br from-blue-50 to-gray-100">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const totalRecords = documents.length;
  const prescriptions = documents.filter(d => d.report_type === 'digital_prescription').length;
  const labReports = documents.filter(d => d.report_type === 'cbc').length;

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <div className="max-w-7xl mx-auto p-4">
        {/* Header - Compact */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-blue-600 rounded-lg flex items-center justify-center shadow-sm">
              <Heart className="w-4 h-4 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">My Health Dashboard</h1>
              {patientId && (
                <p className="text-xs text-gray-500">MRN: {patientId}</p>
              )}
            </div>
          </div>
        </div>

        {/* Stats Cards - Compact */}
        <div className="grid grid-cols-3 gap-3 mb-4">
          <div className="bg-white/80 backdrop-blur-sm rounded-xl border border-gray-100 p-3 text-center shadow-sm">
            <div className="flex items-center justify-center gap-2 mb-1">
              <FileText className="w-4 h-4 text-blue-500" />
              <span className="text-xl font-bold text-gray-800">{totalRecords}</span>
            </div>
            <p className="text-xs text-gray-500">Records</p>
          </div>

          <div className="bg-white/80 backdrop-blur-sm rounded-xl border border-gray-100 p-3 text-center shadow-sm">
            <div className="flex items-center justify-center gap-2 mb-1">
              <Pill className="w-4 h-4 text-green-500" />
              <span className="text-xl font-bold text-gray-800">{prescriptions}</span>
            </div>
            <p className="text-xs text-gray-500">Prescriptions</p>
          </div>

          <div className="bg-white/80 backdrop-blur-sm rounded-xl border border-gray-100 p-3 text-center shadow-sm">
            <div className="flex items-center justify-center gap-2 mb-1">
              <Activity className="w-4 h-4 text-purple-500" />
              <span className="text-xl font-bold text-gray-800">{labReports}</span>
            </div>
            <p className="text-xs text-gray-500">Lab Reports</p>
          </div>
        </div>

        {/* Main Content - Compact */}
        <div className="bg-white/80 backdrop-blur-sm rounded-xl border border-gray-100 overflow-hidden shadow-sm">
          {/* Tabs - Compact */}
          <div className="flex border-b border-gray-100 bg-gray-50/50">
            <button
              onClick={() => setActiveTab('reports')}
              className={`flex-1 py-2.5 text-xs font-medium transition-all flex items-center justify-center gap-1.5 ${
                activeTab === 'reports' 
                  ? 'border-b-2 border-blue-500 text-blue-600 bg-white' 
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              Medical Reports
            </button>
            <button
              onClick={() => setActiveTab('chat')}
              className={`flex-1 py-2.5 text-xs font-medium transition-all flex items-center justify-center gap-1.5 ${
                activeTab === 'chat' 
                  ? 'border-b-2 border-blue-500 text-blue-600 bg-white' 
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <MessageSquare className="w-3.5 h-3.5" />
              AI Health Assistant
            </button>
          </div>

          <div className="p-4">
            {activeTab === 'reports' ? (
              documents.length === 0 ? (
                <div className="text-center py-8">
                  <div className="w-12 h-12 bg-gray-100 rounded-xl flex items-center justify-center mx-auto mb-2">
                    <FileText className="w-6 h-6 text-gray-300" />
                  </div>
                  <p className="text-xs text-gray-500">No medical records found</p>
                </div>
              ) : (
                <div className="space-y-2 max-h-[400px] overflow-y-auto">
                  {documents.map((doc) => (
                    <div key={doc.document_id} className="border border-gray-100 rounded-lg p-3 hover:shadow-sm transition-all hover:border-blue-100">
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-2">
                          <div className="p-1.5 bg-gray-100 rounded-lg">
                            {getReportIcon(doc.report_type)}
                          </div>
                          <div>
                            <h3 className="text-sm font-semibold text-gray-800">{getReportTitle(doc.report_type)}</h3>
                            <p className="text-xs text-gray-500 mt-0.5">
                              {new Date(doc.date).toLocaleDateString()}
                            </p>
                            {doc.report_type === 'digital_prescription' && doc.data?.medications && (
                              <div className="mt-1 text-xs text-gray-600">
                                {doc.data.medications.slice(0, 1).map((med: any, idx: number) => (
                                  <p key={idx} className="flex items-center gap-1">
                                    <Pill className="w-2.5 h-2.5 text-green-500" />
                                    {med.medicine_name} - {med.dosage}
                                  </p>
                                ))}
                                {doc.data.medications.length > 1 && (
                                  <p className="text-xs text-gray-400">+{doc.data.medications.length - 1} more</p>
                                )}
                              </div>
                            )}
                            {doc.report_type === 'cbc' && doc.data?.results && (
                              <div className="mt-1 grid grid-cols-2 gap-1 text-xs">
                                {doc.data.results.slice(0, 2).map((result: any, idx: number) => (
                                  <div key={idx} className="flex justify-between">
                                    <span className="text-gray-600">{result.test_name}:</span>
                                    <span className={result.flag === 'High' ? 'text-red-600 font-medium' : 'text-gray-800'}>
                                      {result.value} {result.unit}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                        <ChevronRight className="w-4 h-4 text-gray-400" />
                      </div>
                    </div>
                  ))}
                </div>
              )
            ) : (
              // AI Health Assistant Chat - Compact
              <div className="flex flex-col h-[480px]">
                {/* Messages Container */}
                <div className="flex-1 overflow-y-auto space-y-3 mb-3 pr-1">
                  {messages.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-center">
                      <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center mb-3 shadow-md">
                        <Brain className="w-6 h-6 text-white" />
                      </div>
                      <h3 className="text-base font-semibold text-gray-900 mb-1">AI Health Assistant</h3>
                      <p className="text-xs text-gray-500 max-w-md mb-3">
                        Ask me anything about your health records
                      </p>
                      <div className="flex flex-wrap gap-2 justify-center">
                        {[
                          "Latest lab results?",
                          "My medications",
                          "Abnormal findings?",
                          "Health summary"
                        ].map((q, idx) => (
                          <button
                            key={idx}
                            onClick={() => {
                              setInput(q);
                              setTimeout(() => handleSendMessage(), 100);
                            }}
                            className="px-3 py-1.5 bg-white border border-gray-200 rounded-full text-xs text-gray-700 hover:border-blue-400 hover:bg-blue-50 transition-all"
                          >
                            {q}
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : (
                    messages.map((msg, idx) => (
                      <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        {msg.role === 'user' ? (
                          <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white px-3 py-1.5 rounded-xl rounded-tr-sm shadow-sm max-w-[75%]">
                            <p className="text-xs">{msg.content}</p>
                          </div>
                        ) : (
                          <div className="max-w-[80%] bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
                            <div className="px-3 py-1.5 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
                              <div className="flex items-center gap-1.5">
                                <div className="w-5 h-5 bg-gradient-to-r from-purple-500 to-blue-500 rounded-full flex items-center justify-center">
                                  <Brain className="w-2.5 h-2.5 text-white" />
                                </div>
                                <span className="text-xs font-medium text-gray-900">AI Assistant</span>
                              </div>
                              <button
                                onClick={() => copyToClipboard(msg.content, idx)}
                                className="text-gray-400 hover:text-gray-600 transition"
                              >
                                {copiedIndex === idx ? <Check className="w-3 h-3 text-green-500" /> : <Copy className="w-3 h-3" />}
                              </button>
                            </div>
                            <div className="px-3 py-2">
                              <div className="prose prose-xs max-w-none text-xs">
                                <ReactMarkdown
                                  remarkPlugins={[remarkGfm]}
                                  rehypePlugins={[rehypeRaw]}
                                  components={{
                                    p: ({node, ...props}) => <p className="text-xs text-gray-700 mb-1 leading-relaxed" {...props} />,
                                    ul: ({node, ...props}) => <ul className="list-disc list-inside mb-1 text-xs" {...props} />,
                                    li: ({node, ...props}) => <li className="text-xs text-gray-700" {...props} />,
                                    strong: ({node, ...props}) => <strong className="font-semibold text-gray-900" {...props} />,
                                  }}
                                >
                                  {msg.content}
                                </ReactMarkdown>
                              </div>
                              {msg.sources && msg.sources.length > 0 && (
                                <div className="mt-2 pt-1 border-t border-gray-100">
                                  <div className="flex items-center gap-1 mb-1">
                                    <Database className="w-2.5 h-2.5 text-gray-400" />
                                    <span className="text-[10px] font-medium text-gray-500">Sources</span>
                                  </div>
                                  <div className="flex flex-wrap gap-1">
                                    {msg.sources.map((source, sidx) => (
                                      <button
                                        key={sidx}
                                        onClick={() => handleCitationClick(source)}
                                        className="flex items-center gap-1 px-1.5 py-0.5 bg-gray-100 hover:bg-blue-100 rounded-md text-[10px] text-gray-600 hover:text-blue-700 transition-all"
                                      >
                                        <FileSearch className="w-2 h-2" />
                                        {source.report_type?.replace('_', ' ')} 
                                      </button>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    ))
                  )}
                  
                  {isLoading && (
                    <div className="flex justify-start">
                      <div className="bg-white border border-gray-200 rounded-xl p-2 shadow-sm">
                        <div className="flex items-center gap-2">
                          <div className="w-6 h-6 bg-gradient-to-r from-purple-500 to-blue-500 rounded-full flex items-center justify-center">
                            <Brain className="w-3 h-3 text-white" />
                          </div>
                          <div className="flex gap-1">
                            <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                            <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                            <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                          </div>
                          <span className="text-xs text-gray-500">Analyzing...</span>
                        </div>
                      </div>
                    </div>
                  )}
                  <div ref={chatEndRef} />
                </div>

                {/* Input Area - Compact with Smaller Buttons */}
                <div className="bg-white rounded-xl border border-gray-200 p-2 shadow-sm">
                  <div className="flex gap-2">
                    <div className="flex-1 relative">
                      <textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder="Ask about your health records..."
                        rows={1}
                        className="w-full px-3 py-2 pr-10 text-sm border border-gray-200 rounded-lg focus:ring-1 focus:ring-blue-500 focus:border-transparent resize-none"
                        style={{ minHeight: '36px', maxHeight: '80px' }}
                        onInput={(e) => {
                          const target = e.target as HTMLTextAreaElement;
                          target.style.height = 'auto';
                          target.style.height = Math.min(target.scrollHeight, 80) + 'px';
                        }}
                      />
                      {isRecording && (
                        <div className="absolute right-10 bottom-2">
                          <div className="flex items-center gap-0.5">
                            <div className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse"></div>
                            <span className="text-[10px] text-red-600">Recording...</span>
                          </div>
                        </div>
                      )}
                    </div>
                    
                    {/* Smaller Voice Button */}
                    <button
                      onClick={isRecording ? handleStopRecording : handleStartRecording}
                      className={`p-2 rounded-lg transition-all duration-200 ${
                        isRecording 
                          ? 'bg-red-100 text-red-600 animate-pulse ring-1 ring-red-400' 
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                      title={isRecording ? "Stop recording" : "Start voice input"}
                    >
                      {isRecording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                    </button>
                    
                    {/* Smaller Send Button */}
                    <button
                      onClick={handleSendMessage}
                      disabled={isLoading || !input.trim()}
                      className="px-3 py-2 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-lg hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 transition-all flex items-center gap-1 text-sm"
                    >
                      <Send className="w-3.5 h-3.5" />
                      Send
                    </button>
                  </div>
                  
                  {/* Disclaimer - Compact */}
                  <div className="flex items-center justify-between mt-2 text-[10px]">
                    <div className="flex items-center gap-1.5 text-amber-600 bg-amber-50 px-2 py-1 rounded-md">
                      <Shield className="w-3 h-3" />
                      <span>AI responses are informational only. Consult your doctor.</span>
                    </div>
                    <div className="flex items-center gap-1 text-gray-400">
                      <Sparkles className="w-3 h-3" />
                      <span>RAG + LLM</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}