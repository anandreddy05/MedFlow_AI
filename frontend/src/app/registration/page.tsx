'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/hooks/useAuth';

export default function RegistrationPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [step, setStep] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  interface DoctorOption {
    doctor_id: number;
    full_name: string;
    email: string;
  }

  const [doctors, setDoctors] = useState<DoctorOption[]>([]);
  const [loadingDoctors, setLoadingDoctors] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: '',
    role: 'patient',
    date_of_birth: '',
    gender: '',
    phone: '',
    assigned_doctor_id: '',
    department: 'General OPD',
  });

  const roles = [
    { value: 'patient', label: 'Patient' },
    { value: 'doctor', label: 'Doctor' },
    { value: 'nurse', label: 'Nurse' },
    { value: 'finance', label: 'Finance' },
    { value: 'admin', label: 'Admin' },
    { value: 'registration', label: 'Registration' },
  ];

  // Fetch doctors from backend when role is patient
  useEffect(() => {
    const fetchDoctors = async () => {
      if (formData.role !== 'patient') return;
      
      setLoadingDoctors(true);
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch('http://localhost:8000/registration/available-doctors', {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });
        
        if (response.ok) {
          const data = await response.json();
          setDoctors(data);
        } else {
          setDoctors([]);
        }
      } catch (error) {
        console.error('Error fetching doctors:', error);
        setDoctors([]);
      } finally {
        setLoadingDoctors(false);
      }
    };
    
    fetchDoctors();
  }, [formData.role]);

  const handleSubmit = async () => {
    setIsLoading(true);
    setError('');
    setSuccess('');
  
    try {
      const token = localStorage.getItem('access_token');
  
      if (formData.role === 'patient') {
        const params = new URLSearchParams({
          full_name: formData.full_name,
          date_of_birth: formData.date_of_birth,
          gender: formData.gender,
          phone: formData.phone,
          email: formData.email,
          assigned_doctor_id: formData.assigned_doctor_id,
          department: formData.department,
          password: formData.password,
        });
  
        const response = await fetch(
          `http://localhost:8000/registration/create-patient?${params.toString()}`,
          {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          }
        );
  
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Patient registration failed');
        }
  
        const result = await response.json();
        setSuccess(`Patient registered! MRN: ${result.mrn}, Temp Password: ${result.temporary_password}`);
  
      } else {
        const payload = {
          email: formData.email,
          full_name: formData.full_name,
          password: formData.password,
          role: formData.role,
        };
  
        const response = await fetch('http://localhost:8000/auth/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
  
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Registration failed');
        }
  
        setSuccess(`${formData.role} registered successfully!`);
      }
  
      setTimeout(() => {
        setStep(1);
        setFormData({
          email: '',
          password: '',
          full_name: '',
          role: 'patient',
          date_of_birth: '',
          gender: '',
          phone: '',
          assigned_doctor_id: '',
          department: 'General OPD',
        });
        setSuccess('');
      }, 3000);
  
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    } finally {
      setIsLoading(false);
    }
  };

  const updateField = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto p-6">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">User Registration</h1>
          <p className="text-gray-600">Register doctors, nurses, patients, and staff</p>
        </div>

        {success && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg text-green-700">
            {success}
          </div>
        )}

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        <div className="bg-white rounded-xl border p-6">
          {step === 1 && (
            <div>
              <h2 className="text-lg font-semibold mb-4">Select Role</h2>
              <div className="grid grid-cols-3 gap-4">
                {roles.map((role) => (
                  <button
                    key={role.value}
                    type="button"
                    onClick={() => {
                      updateField('role', role.value);
                      setStep(2);
                    }}
                    className="p-4 rounded-xl border-2 border-gray-200 text-center hover:border-blue-500 hover:bg-blue-50 transition"
                  >
                    <p className="font-medium">{role.label}</p>
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === 2 && (
            <div>
              <h2 className="text-lg font-semibold mb-4">Account Details</h2>
              <div className="space-y-4">
                {formData.role === 'patient' && (
                  <>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium mb-1">Date of Birth *</label>
                        <input
                          type="date"
                          required
                          value={formData.date_of_birth}
                          onChange={(e) => updateField('date_of_birth', e.target.value)}
                          className="w-full px-3 py-2 border rounded-lg"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-1">Gender *</label>
                        <select
                          required
                          value={formData.gender}
                          onChange={(e) => updateField('gender', e.target.value)}
                          className="w-full px-3 py-2 border rounded-lg"
                        >
                          <option value="">Select</option>
                          <option value="male">Male</option>
                          <option value="female">Female</option>
                        </select>
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-1">Phone</label>
                      <input
                        type="tel"
                        value={formData.phone}
                        onChange={(e) => updateField('phone', e.target.value)}
                        className="w-full px-3 py-2 border rounded-lg"
                        placeholder="Phone number"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-1">Assign Doctor *</label>
                      {loadingDoctors ? (
                        <div className="text-gray-500">Loading doctors...</div>
                      ) : doctors.length === 0 ? (
                        <div className="text-red-500 text-sm">
                          No doctors available. Please create a doctor first.
                        </div>
                      ) : (
                        <select
                          required
                          value={formData.assigned_doctor_id}
                          onChange={(e) => updateField('assigned_doctor_id', e.target.value)}
                          className="w-full px-3 py-2 border rounded-lg"
                        >
                          <option value="">Select a doctor</option>
                          {doctors.map((doctor) => (
                            <option key={doctor.doctor_id} value={doctor.doctor_id}>
                              Dr. {doctor.full_name} ({doctor.email})
                            </option>
                          ))}
                        </select>
                      )}
                    </div>
                  </>
                )}

                <div>
                  <label className="block text-sm font-medium mb-1">Full Name *</label>
                  <input
                    type="text"
                    required
                    value={formData.full_name}
                    onChange={(e) => updateField('full_name', e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="Full name"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Email *</label>
                  <input
                    type="email"
                    required
                    value={formData.email}
                    onChange={(e) => updateField('email', e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="Email address"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Password *</label>
                  <input
                    type="password"
                    required
                    value={formData.password}
                    onChange={(e) => updateField('password', e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="Password"
                  />
                </div>
              </div>

              <div className="mt-6 flex justify-between">
                <button onClick={() => setStep(1)} className="px-6 py-2 border rounded-lg">
                  Back
                </button>
                <button 
                  onClick={handleSubmit}
                  disabled={isLoading}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg disabled:opacity-50"
                >
                  {isLoading ? 'Registering...' : 'Register'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
