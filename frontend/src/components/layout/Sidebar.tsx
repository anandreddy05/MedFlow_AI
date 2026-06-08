'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/lib/hooks/useAuth';
import { FileText, MessageSquare, LogOut, Activity, Users, UserPlus, ClipboardList, Upload, Clock, Pill, Stethoscope, Building, CreditCard, LayoutDashboard } from 'lucide-react';

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  
  const getNavItems = () => {
    const role = user?.role;
    
    if (role === 'admin') {
      return [
        { name: 'Dashboard', href: '/admin', icon: LayoutDashboard },
        { name: 'Users', href: '/admin/users', icon: Users },
        { name: 'Audit Logs', href: '/admin/logs', icon: ClipboardList },
      ];
    }
    
    if (role === 'registration') {
      return [
        { name: 'Register Patient', href: '/registration', icon: UserPlus },
      ];
    }
    
    if (role === 'doctor') {
      return [
        { name: 'My Patients', href: '/doctor', icon: Users },
        { name: 'Write Prescription', href: '/doctor/prescription', icon: Pill },
      ];
    }
    
    if (role === 'nurse') {
      return [
        { name: 'Upload', href: '/nurse/upload', icon: Upload },
        { name: 'Pending Reviews', href: '/nurse/pending', icon: Clock },
      ];
    }
    
    if (role === 'patient') {
      return [
        { name: 'My Records', href: '/patient', icon: FileText },
        { name: 'AI Chat', href: '/patient', icon: MessageSquare },
      ];
    }
    
    if (role === 'finance') {
      return [
        { name: 'Invoices', href: '/finance/invoices', icon: CreditCard },
      ];
    }
    
    return [{ name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard }];
  };

  const navItems = getNavItems();
  if (!user) return null;

  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-white border-r border-gray-200 z-50">
      <div className="flex flex-col h-full">
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <Activity className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-gray-900">MedFlow AI</span>
          </div>
          <div className="mt-3 pt-3 border-t border-gray-100">
            <p className="text-sm font-medium text-gray-900">{user.full_name || user.email}</p>
            <p className="text-xs text-gray-500 capitalize mt-0.5">{user.role}</p>
          </div>
        </div>

        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const isActive =
              pathname === item.href ||
              (item.href !== '/admin' && pathname.startsWith(item.href));
            return (
              <Link key={item.name} href={item.href} className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${isActive ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-600 hover:bg-gray-50'}`}>
                <item.icon className="w-4 h-4" />
                {item.name}
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-gray-100">
          <button onClick={logout} className="flex items-center gap-3 px-3 py-2 w-full rounded-lg text-sm text-gray-600 hover:bg-gray-50">
            <LogOut className="w-4 h-4" />
            Logout
          </button>
        </div>
      </div>
    </aside>
  );
}
