'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { 
  ArrowLeft, Save, FileText, Pill, Clock, 
  Plus, Trash2, Printer, Eye, Calendar,
  User, Stethoscope, AlertCircle, CheckCircle
} from 'lucide-react';
import { API_BASE_URL } from '@/lib/api/client';

interface Medication {
  id: string;
  name: string;
  dosage: string;
  timing: string[];
  foodInstruction: string;
  duration: string;
  notes: string;
}

interface PreviousPrescription {
  id: string;
  date: string;
  doctor: string;
  medications: Medication[];
  instructions: string;
}

function WritePrescriptionContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const patientId = searchParams.get('patient');
  
  const [patient, setPatient] = useState<any>(null);
  const [previousPrescriptions, setPreviousPrescriptions] = useState<PreviousPrescription[]>([]);
  const [instructions, setInstructions] = useState('');
  const [medications, setMedications] = useState<Medication[]>([
    { id: '1', name: '', dosage: '', timing: [], foodInstruction: 'before', duration: '', notes: '' }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'new' | 'previous'>('new');

  // Fetch patient details
  useEffect(() => {
    const fetchPatient = async () => {
      if (!patientId) return;
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`${API_BASE_URL}/doctor/patient/${patientId}/full-history`, {
          headers: { 'Authorization': `Bearer ${token}` },
        });
        if (response.ok) {
          const data = await response.json();
          setPatient(data.patient);
          // Extract previous prescriptions from documents
          const prescriptions = data.documents
            ?.filter((doc: any) => doc.report_type === 'digital_prescription')
            .map((doc: any) => ({
              id: doc.document_id,
              date: doc.created_at,
              doctor: 'Dr. Rahul Verma',
              medications: doc.data?.medications || [],
              instructions: doc.data?.clinical_notes || ''
            })) || [];
          setPreviousPrescriptions(prescriptions);
        }
      } catch (error) {
        console.error('Failed to fetch patient:', error);
      }
    };
    fetchPatient();
  }, [patientId]);

  const addMedication = () => {
    setMedications([
      ...medications,
      { id: Date.now().toString(), name: '', dosage: '', timing: [], foodInstruction: 'before', duration: '', notes: '' }
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

  const handleSubmit = async () => {
    if (!patientId || !patient) return;
    
    setIsLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const payload = {
        patient_id: patientId,
        doctor_id: JSON.parse(localStorage.getItem('user') || '{}').id,
        instructions: instructions,
        medications: medications.filter(m => m.name.trim()).map(m => ({
          medicine_name: m.name,
          dosage: m.dosage,
          timing: m.timing[0] || 'morning',
          food_instruction: m.foodInstruction,
          frequency: 'daily'
        }))
      };

      const response = await fetch(`${API_BASE_URL}/prescriptions/direct`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        alert('Prescription saved successfully!');
        router.back();
      } else {
        const error = await response.json();
        alert('Failed to save prescription: ' + error.detail);
      }
    } catch (error) {
      console.error('Error saving prescription:', error);
      alert('Failed to save prescription');
    } finally {
      setIsLoading(false);
    }
  };

  const timingOptions = ['Morning', 'Afternoon', 'Evening', 'Night'];
  const foodOptions = ['Before Food', 'After Food', 'With Food', 'Independent'];

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.back()}
              className="p-2 hover:bg-gray-100 rounded-lg transition"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </button>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Write Prescription</h1>
              {patient && (
                <p className="text-sm text-gray-500 mt-0.5">
                  Patient: {patient.full_name} (MRN: {patient.patient_id})
                </p>
              )}
            </div>
          </div>
          <div className="flex gap-2">
            <button className="px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50 flex items-center gap-2">
              <Save className="w-4 h-4" />
              Save as Draft
            </button>
            <button 
              onClick={handleSubmit}
              disabled={isLoading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 flex items-center gap-2"
            >
              <CheckCircle className="w-4 h-4" />
              {isLoading ? 'Saving...' : 'Save & Generate PDF'}
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden mb-6">
          <div className="flex border-b border-gray-200">
            <button
              onClick={() => setActiveTab('new')}
              className={`px-6 py-3 text-sm font-medium transition ${
                activeTab === 'new' 
                  ? 'border-b-2 border-blue-500 text-blue-600 bg-white' 
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <Pill className="w-4 h-4 inline mr-2" />
              New Prescription
            </button>
            <button
              onClick={() => setActiveTab('previous')}
              className={`px-6 py-3 text-sm font-medium transition ${
                activeTab === 'previous' 
                  ? 'border-b-2 border-blue-500 text-blue-600 bg-white' 
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <Clock className="w-4 h-4 inline mr-2" />
              Previous Prescriptions
            </button>
          </div>

          <div className="p-6">
            {activeTab === 'new' ? (
              <div className="space-y-6">
                {/* Prescription Instructions */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Prescription / Instructions
                  </label>
                  <textarea
                    value={instructions}
                    onChange={(e) => setInstructions(e.target.value)}
                    rows={4}
                    placeholder="Enter diagnosis, instructions, and notes for the patient..."
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                {/* Medications Section */}
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-md font-semibold text-gray-900">Medications</h3>
                    <button
                      onClick={addMedication}
                      className="px-3 py-1.5 text-sm bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 flex items-center gap-1"
                    >
                      <Plus className="w-4 h-4" />
                      Add Another Medicine
                    </button>
                  </div>

                  <div className="space-y-4">
                    {medications.map((med) => (
                      <div key={med.id} className="border border-gray-200 rounded-lg p-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                          <div>
                            <label className="block text-xs font-medium text-gray-500 mb-1">
                              Medicine Name & Dose
                            </label>
                            <div className="flex gap-2">
                              <input
                                type="text"
                                value={med.name}
                                onChange={(e) => updateMedication(med.id, 'name', e.target.value)}
                                placeholder="e.g., Paracetamol 650mg"
                                className="flex-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg"
                              />
                            </div>
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-gray-500 mb-1">
                              Duration
                            </label>
                            <input
                              type="text"
                              value={med.duration}
                              onChange={(e) => updateMedication(med.id, 'duration', e.target.value)}
                              placeholder="e.g., 7 days"
                              className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg"
                            />
                          </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                          <div>
                            <label className="block text-xs font-medium text-gray-500 mb-2">
                              Timing (Select all that apply)
                            </label>
                            <div className="flex flex-wrap gap-3">
                              {timingOptions.map((t) => (
                                <label key={t} className="flex items-center gap-2">
                                  <input
                                    type="checkbox"
                                    checked={med.timing.includes(t)}
                                    onChange={() => toggleTiming(med.id, t)}
                                    className="w-4 h-4 text-blue-600 rounded border-gray-300"
                                  />
                                  <span className="text-sm text-gray-700">{t}</span>
                                </label>
                              ))}
                            </div>
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-gray-500 mb-2">
                              Before / After Food
                            </label>
                            <div className="flex flex-wrap gap-3">
                              {foodOptions.map((f) => (
                                <label key={f} className="flex items-center gap-2">
                                  <input
                                    type="radio"
                                    name={`food-${med.id}`}
                                    checked={med.foodInstruction === f.toLowerCase().replace(' ', '_')}
                                    onChange={() => updateMedication(med.id, 'foodInstruction', f.toLowerCase().replace(' ', '_'))}
                                    className="w-4 h-4 text-blue-600"
                                  />
                                  <span className="text-sm text-gray-700">{f}</span>
                                </label>
                              ))}
                            </div>
                          </div>
                        </div>

                        {medications.length > 1 && (
                          <div className="flex justify-end">
                            <button
                              onClick={() => removeMedication(med.id)}
                              className="text-red-500 text-sm hover:text-red-700 flex items-center gap-1"
                            >
                              <Trash2 className="w-3 h-3" />
                              Remove
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              // Previous Prescriptions
              <div className="space-y-4">
                {previousPrescriptions.length === 0 ? (
                  <div className="text-center py-12">
                    <FileText className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                    <p className="text-gray-500">No previous prescriptions found</p>
                  </div>
                ) : (
                  previousPrescriptions.map((prescription) => (
                    <div key={prescription.id} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                            <FileText className="w-5 h-5 text-blue-600" />
                          </div>
                          <div>
                            <p className="font-medium text-gray-900">
                              Prescription dated {new Date(prescription.date).toLocaleDateString()}
                            </p>
                            <p className="text-sm text-gray-500">By {prescription.doctor}</p>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <button className="p-1.5 text-gray-400 hover:text-blue-600 transition">
                            <Eye className="w-4 h-4" />
                          </button>
                          <button className="p-1.5 text-gray-400 hover:text-blue-600 transition">
                            <Printer className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                      
                      <div className="mt-3 space-y-2">
                        <p className="text-sm font-medium text-gray-700">Medications:</p>
                        {prescription.medications.map((med, idx) => (
                          <div key={idx} className="flex items-center justify-between text-sm py-1 border-b border-gray-100">
                            <div>
                              <span className="font-medium">{med.name}</span>
                              <span className="text-gray-500 ml-2">{med.dosage}</span>
                            </div>
                            <div className="flex gap-3 text-xs text-gray-500">
                              <span className="capitalize">{Array.isArray(med.timing) ? med.timing.join(', ') : med.timing}</span>
                              <span className="capitalize">{med.foodInstruction?.replace('_', ' ')}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                      
                      {prescription.instructions && (
                        <div className="mt-3 p-2 bg-gray-50 rounded-lg">
                          <p className="text-xs text-gray-600">{prescription.instructions}</p>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function WritePrescriptionPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-screen">
          <p className="text-gray-500">Loading prescription...</p>
        </div>
      }
    >
      <WritePrescriptionContent />
    </Suspense>
  );
}
