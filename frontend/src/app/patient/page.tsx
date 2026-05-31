'use client';

import dynamic from 'next/dynamic';
import { Loader2 } from 'lucide-react';

const PatientDashboardClient = dynamic(
  () => import('./PatientDashboardClient'),
  { 
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center h-screen bg-gradient-to-br from-blue-50 to-gray-100">
        <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
      </div>
    )
  }
);

export default function PatientPage() {
  return <PatientDashboardClient />;
}