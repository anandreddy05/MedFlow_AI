'use client';

import { useState, useEffect, useRef } from 'react';
import { 
  Shield, Brain, Send, Mic, MicOff, 
  Database, FileSearch, Zap, Copy, Check,
  Sparkles, AlertCircle, MessageSquare
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { useReactMediaRecorder } from 'react-media-recorder';

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

export default function FinanceDashboard() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [isClient, setIsClient] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setIsClient(true);
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
        formData.append('audio', blob, 'finance_voice.webm');

        const response = await fetch('http://127.0.0.1:8000/chat/voice', {
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

  const handleSendMessage = async () => {
    if (!input.trim()) return;

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
    alert(`Document: ${source.report_type?.replace('_', ' ')}\nConfidence: ${Math.round(source.score * 100)}%`);
  };

  const isRecording = status === 'recording';

  if (!isClient) {
    return (
      <div className="flex items-center justify-center h-screen bg-gradient-to-br from-purple-50 to-gray-100">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <div className="max-w-5xl mx-auto p-6">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-gradient-to-r from-purple-600 to-indigo-600 rounded-xl flex items-center justify-center shadow-md">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-700 to-indigo-700 bg-clip-text text-transparent">
                Finance & Compliance Assistant
              </h1>
              <p className="text-sm text-gray-500">
                Ask questions about healthcare regulations, billing codes, and financial policies
              </p>
            </div>
          </div>
        </div>

        {/* Chat Container */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
          {/* Messages Area - Same as Doctor's Chat */}
          <div className="h-[550px] overflow-y-auto p-4 space-y-4">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-2xl flex items-center justify-center mb-4 shadow-lg">
                  <Brain className="w-8 h-8 text-white" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Compliance & Finance Assistant</h3>
                <p className="text-sm text-gray-500 max-w-md mb-6">
                  Ask me about healthcare regulations, billing codes, financial policies, and compliance requirements.
                </p>
                <div className="flex flex-wrap gap-2 justify-center">
                  {[
                    "What are the seven elements of a compliance program?",
                    "What is the discount for uninsured patients?",
                    "How long to submit Medicare claims?",
                    "What are penalties for false claims?"
                  ].map((q, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        setInput(q);
                        setTimeout(() => handleSendMessage(), 100);
                      }}
                      className="px-3 py-1.5 bg-white border border-gray-200 rounded-full text-xs text-gray-700 hover:border-purple-400 hover:bg-purple-50 transition-all"
                    >
                      {q.length > 50 ? q.substring(0, 50) + '...' : q}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg, idx) => (
                <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {msg.role === 'user' ? (
                    <div className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-4 py-2 rounded-2xl rounded-tr-sm shadow-sm max-w-[75%]">
                      <p className="text-sm">{msg.content}</p>
                    </div>
                  ) : (
                    <div className="max-w-[80%] bg-white border border-gray-200 rounded-2xl shadow-sm overflow-hidden">
                      <div className="px-4 py-2 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
                        <div className="flex items-center gap-2">
                          <div className="w-6 h-6 bg-gradient-to-r from-purple-500 to-indigo-500 rounded-full flex items-center justify-center">
                            <Brain className="w-3 h-3 text-white" />
                          </div>
                          <span className="text-sm font-medium text-gray-900">Compliance Assistant</span>
                        </div>
                        <button
                          onClick={() => copyToClipboard(msg.content, idx)}
                          className="text-gray-400 hover:text-gray-600 transition"
                        >
                          {copiedIndex === idx ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
                        </button>
                      </div>

                      <div className="px-4 py-3">
                        <div className="prose prose-sm max-w-none">
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            rehypePlugins={[rehypeRaw]}
                            components={{
                              p: ({node, ...props}) => <p className="text-sm text-gray-700 mb-2 leading-relaxed" {...props} />,
                              ul: ({node, ...props}) => <ul className="list-disc list-inside mb-2 space-y-1" {...props} />,
                              ol: ({node, ...props}) => <ol className="list-decimal list-inside mb-2 space-y-1" {...props} />,
                              li: ({node, ...props}) => <li className="text-sm text-gray-700" {...props} />,
                              strong: ({node, ...props}) => <strong className="font-semibold text-gray-900" {...props} />,
                            }}
                          >
                            {msg.content}
                          </ReactMarkdown>
                        </div>

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
                                  className="flex items-center gap-1.5 px-2.5 py-1.5 bg-gray-100 hover:bg-purple-100 rounded-lg text-xs text-gray-600 hover:text-purple-700 transition-all"
                                >
                                  <FileSearch className="w-3 h-3" />
                                  {source.report_type?.replace('_', ' ')} 
                                  <span className="text-gray-400">•</span>
                                  <Zap className="w-2.5 h-2.5 text-amber-500" />
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
                <div className="bg-white border border-gray-200 rounded-2xl p-3 shadow-sm">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 bg-gradient-to-r from-purple-500 to-indigo-500 rounded-full flex items-center justify-center">
                      <Brain className="w-3 h-3 text-white" />
                    </div>
                    <div className="flex gap-1">
                      <div className="w-1.5 h-1.5 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                      <div className="w-1.5 h-1.5 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                      <div className="w-1.5 h-1.5 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    </div>
                    <span className="text-sm text-gray-500 ml-2">Searching compliance documents...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Input Area - Same as Doctor's Chat */}
          <div className="bg-white border-t border-gray-200 p-4">
            <div className="flex gap-3">
              <div className="flex-1 relative">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask about compliance, billing codes, financial policies..."
                  rows={1}
                  className="w-full px-4 py-3 pr-12 text-sm border border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
                  style={{ minHeight: '48px', maxHeight: '120px' }}
                  onInput={(e) => {
                    const target = e.target as HTMLTextAreaElement;
                    target.style.height = 'auto';
                    target.style.height = Math.min(target.scrollHeight, 120) + 'px';
                  }}
                />
                {isRecording && (
                  <div className="absolute right-14 bottom-3">
                    <div className="flex items-center gap-1">
                      <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                      <span className="text-xs text-red-600">Recording...</span>
                    </div>
                  </div>
                )}
              </div>
              
              {/* Voice Button */}
              <button
                onClick={isRecording ? handleStopRecording : handleStartRecording}
                className={`p-3 rounded-xl transition-all duration-200 ${
                  isRecording 
                    ? 'bg-red-100 text-red-600 animate-pulse ring-2 ring-red-400 ring-offset-2' 
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
                title={isRecording ? "Stop recording" : "Start voice input"}
              >
                {isRecording ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
              </button>
              
              {/* Send Button */}
              <button
                onClick={handleSendMessage}
                disabled={isLoading || !input.trim()}
                className="px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 transition-all flex items-center gap-2 shadow-md"
              >
                <Send className="w-4 h-4" />
                Send
              </button>
            </div>
            
            {/* Disclaimer */}
            <div className="flex items-center justify-between mt-3 text-xs">
              <div className="flex items-center gap-2 text-amber-600 bg-amber-50 px-3 py-1.5 rounded-lg">
                <AlertCircle className="w-3.5 h-3.5" />
                <span>Responses based on uploaded compliance documents and policies</span>
              </div>
              <div className="flex items-center gap-2 text-gray-400">
                <Sparkles className="w-3.5 h-3.5" />
                <span>RAG + LLM</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
