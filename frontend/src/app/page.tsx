'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/hooks/useAuth';

const getRoleDashboard = (role: string): string => {
    switch (role) {
        case 'doctor': return '/doctor';
        case 'nurse': return '/nurse';
        case 'patient': return '/patient';
        case 'finance': return '/finance';
        case 'admin': return '/admin';
        case 'registration': return '/registration';
        default: return '/login';
    }
};

export default function HomePage() {
    const { isAuthenticated, isLoading, user } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (!isLoading) {
            if (isAuthenticated && user) {
                const dashboardPath = getRoleDashboard(user.role);
                router.replace(dashboardPath);
            } else {
                router.replace('/login');
            }
        }
    }, [isAuthenticated, isLoading, user, router]);

    return (
        <div className="min-h-screen flex items-center justify-center">
            <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                <p className="mt-4 text-gray-600">Loading MedFlow AI...</p>
            </div>
        </div>
    );
}
