'use client';

import React from "react";
import { useState, useEffect } from 'react';
import { UserPlus, Edit, Trash2, Shield, Stethoscope, Briefcase, Building, User } from 'lucide-react';
import { API_BASE_URL } from '@/lib/api/client';

interface AdminUser {
  id: number;
  email: string;
  full_name: string;
  role: string;
  created_at: string;
}

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: '',
    role: 'registration',
  });
  const [message, setMessage] = useState('');

  const roles = [
    { value: 'admin', label: 'Admin', icon: Shield, color: 'red', description: 'Full system access' },
    { value: 'registration', label: 'Registration', icon: Building, color: 'blue', description: 'Register patients' },
    { value: 'doctor', label: 'Doctor', icon: Stethoscope, color: 'green', description: 'Treat patients' },
    { value: 'nurse', label: 'Nurse', icon: Briefcase, color: 'purple', description: 'Upload documents' },
    { value: 'finance', label: 'Finance', icon: Building, color: 'amber', description: 'Billing' },
  ];

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_BASE_URL}/admin/users`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setUsers(data.users || []);
      }
    } catch (error) {
      console.error('Failed to fetch users:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async (
    e: React.FormEvent<HTMLFormElement>
  ) => {
    e.preventDefault();
    setMessage('');
    
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_BASE_URL}/auth/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(formData),
      });
      
      if (response.ok) {
        const result = await response.json();
        setMessage(`✅ ${formData.role} created successfully! Temp password: ${formData.password}`);
        setFormData({ email: '', password: '', full_name: '', role: 'registration' });
        fetchUsers();
        setTimeout(() => setShowModal(false), 2000);
      } else {
        const error = await response.json();
        setMessage(`❌ Error: ${error.detail || 'Creation failed'}`);
      }
    } catch (error) {
      setMessage('❌ Network error');
    }
  };

  const getRoleIcon = (role: string) => {
    const r = roles.find(r => r.value === role);
    if (r) return r.icon;
    return User;
  };

  const getRoleColor = (role: string) => {
    const r = roles.find(r => r.value === role);
    return r?.color || 'gray';
  };

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">User Management</h1>
          <p className="text-gray-600 mt-1">Create and manage system users</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg flex items-center gap-2 hover:bg-blue-700"
        >
          <UserPlus className="w-4 h-4" />
          Create User
        </button>
      </div>

      {/* Users Table */}
      <div className="bg-white rounded-xl border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left p-4 text-sm font-medium text-gray-600">User</th>
                <th className="text-left p-4 text-sm font-medium text-gray-600">Email</th>
                <th className="text-left p-4 text-sm font-medium text-gray-600">Role</th>
                <th className="text-left p-4 text-sm font-medium text-gray-600">Status</th>
                <th className="text-left p-4 text-sm font-medium text-gray-600">Created</th>
                <th className="text-left p-4 text-sm font-medium text-gray-600">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {users.map((user) => {
                const Icon = getRoleIcon(user.role);
                const color = getRoleColor(user.role);
                return (
                  <tr key={user.id} className="hover:bg-gray-50">
                    <td className="p-4">
                      <div className="flex items-center gap-3">
                        <div className={`w-8 h-8 bg-${color}-100 rounded-lg flex items-center justify-center`}>
                          <Icon className={`w-4 h-4 text-${color}-600`} />
                        </div>
                        <span className="font-medium text-gray-900">{user.full_name}</span>
                      </div>
                    </td>
                    <td className="p-4 text-gray-600">{user.email}</td>
                    <td className="p-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium capitalize bg-${color}-100 text-${color}-700`}>
                        {user.role}
                      </span>
                    </td>
                    <td className="p-4">
                      <span className="px-2 py-1 rounded-full text-xs bg-green-100 text-green-700">Active</span>
                    </td>
                    <td className="p-4 text-gray-500 text-sm">{new Date(user.created_at).toLocaleDateString()}</td>
                    <td className="p-4">
                      <div className="flex gap-2">
                        <button className="p-1 text-gray-400 hover:text-blue-600">
                          <Edit className="w-4 h-4" />
                        </button>
                        <button className="p-1 text-gray-400 hover:text-red-600">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create User Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">Create New User</h2>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600">✕</button>
            </div>

            {message && (
              <div className="mb-4 p-3 bg-blue-50 rounded-lg text-sm">
                {message}
              </div>
            )}

            <form onSubmit={handleCreateUser} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Role *</label>
                <select
                  required
                  value={formData.role}
                  onChange={(e) => setFormData({...formData, role: e.target.value})}
                  className="w-full px-3 py-2 border rounded-lg"
                >
                  {roles.map(role => (
                    <option key={role.value} value={role.value}>{role.label}</option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  {roles.find(r => r.value === formData.role)?.description}
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Full Name *</label>
                <input
                  type="text"
                  required
                  value={formData.full_name}
                  onChange={(e) => setFormData({...formData, full_name: e.target.value})}
                  className="w-full px-3 py-2 border rounded-lg"
                  placeholder="e.g., Dr. Sarah Smith"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Email *</label>
                <input
                  type="email"
                  required
                  value={formData.email}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                  className="w-full px-3 py-2 border rounded-lg"
                  placeholder="user@hospital.com"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Temporary Password *</label>
                <input
                  type="text"
                  required
                  value={formData.password}
                  onChange={(e) => setFormData({...formData, password: e.target.value})}
                  className="w-full px-3 py-2 border rounded-lg"
                  placeholder="Temp password (user will be forced to change)"
                />
              </div>

              <button
                type="submit"
                className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700"
              >
                Create User
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
