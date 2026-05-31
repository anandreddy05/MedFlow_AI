'use client';

import { useState, useEffect } from 'react';
import { CreditCard, DollarSign, FileText, TrendingUp } from 'lucide-react';

export default function FinanceDashboard() {
  const [invoices, setInvoices] = useState([]);
  const [stats, setStats] = useState({
    totalInvoices: 0,
    totalAmount: 0,
    pendingPayments: 0,
  });

  useEffect(() => {
    const fetchInvoices = async () => {
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch('http://localhost:8000/finance/invoices', {
          headers: { 'Authorization': `Bearer ${token}` },
        });
        if (response.ok) {
          const data = await response.json();
          setInvoices(data.invoices || []);
          setStats({
            totalInvoices: data.invoices?.length || 0,
            totalAmount: data.invoices?.reduce((sum: number, inv: any) => 
              sum + (inv.financial_data?.total_amount_due || 0), 0),
            pendingPayments: data.invoices?.filter((inv: any) => 
              inv.financial_data?.status !== 'paid').length || 0,
          });
        }
      } catch (error) {
        console.error('Failed to fetch invoices:', error);
      }
    };
    fetchInvoices();
  }, []);

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Finance Dashboard</h1>
        <p className="text-gray-600 mt-1">Manage medical invoices and billing</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-xl border p-6">
          <div className="p-2 bg-blue-50 rounded-lg w-fit mb-4">
            <FileText className="w-5 h-5 text-blue-600" />
          </div>
          <p className="text-2xl font-bold">{stats.totalInvoices}</p>
          <p className="text-sm text-gray-600">Total Invoices</p>
        </div>

        <div className="bg-white rounded-xl border p-6">
          <div className="p-2 bg-green-50 rounded-lg w-fit mb-4">
            <DollarSign className="w-5 h-5 text-green-600" />
          </div>
          <p className="text-2xl font-bold">₹{stats.totalAmount.toLocaleString()}</p>
          <p className="text-sm text-gray-600">Total Revenue</p>
        </div>

        <div className="bg-white rounded-xl border p-6">
          <div className="p-2 bg-yellow-50 rounded-lg w-fit mb-4">
            <CreditCard className="w-5 h-5 text-yellow-600" />
          </div>
          <p className="text-2xl font-bold">{stats.pendingPayments}</p>
          <p className="text-sm text-gray-600">Pending Payments</p>
        </div>

        <div className="bg-white rounded-xl border p-6">
          <div className="p-2 bg-purple-50 rounded-lg w-fit mb-4">
            <TrendingUp className="w-5 h-5 text-purple-600" />
          </div>
          <p className="text-2xl font-bold">+12%</p>
          <p className="text-sm text-gray-600">vs Last Month</p>
        </div>
      </div>

      <div className="bg-white rounded-xl border">
        <div className="p-4 border-b">
          <h3 className="font-semibold">Recent Invoices</h3>
        </div>
        <div className="divide-y">
          {invoices.length === 0 ? (
            <div className="p-8 text-center text-gray-500">No invoices found</div>
          ) : (
            invoices.slice(0, 10).map((invoice: any, idx: number) => (
              <div key={idx} className="p-4 flex items-center justify-between">
                <div>
                  <p className="font-medium">Invoice #{invoice.document_id?.slice(-8)}</p>
                  <p className="text-sm text-gray-500">Patient ID: {invoice.patient_id}</p>
                  <p className="text-xs text-gray-400">
                    {invoice.approved_at ? new Date(invoice.approved_at).toLocaleDateString() : 'Pending'}
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-bold text-lg">₹{invoice.financial_data?.total_amount_due?.toLocaleString() || 0}</p>
                  <button className="text-blue-600 text-sm hover:underline">View Details →</button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}