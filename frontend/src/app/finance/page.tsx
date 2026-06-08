'use client';

import dynamic from 'next/dynamic';

// Dynamically import the dashboard and explicitly disable Server-Side Rendering
const FinanceDashboard = dynamic(
  () => import('./FinanceDashboard'),
  { ssr: false }
);

export default function FinancePage() {
  return <FinanceDashboard />;
}