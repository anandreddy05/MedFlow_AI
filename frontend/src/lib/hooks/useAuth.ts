'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

interface User {
    id: number;
    email: string;
    full_name: string;
    role: string;
}

interface AuthContextType {
    user: User | null;
    isLoading: boolean;
    login: (credentials: { username: string; password: string }) => Promise<void>;
    logout: () => void;
    isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const router = useRouter();

    useEffect(() => {
        const token = localStorage.getItem('access_token');
        const storedUser = localStorage.getItem('user');
        if (token && storedUser) {
            try {
                setUser(JSON.parse(storedUser));
            } catch (e) {
                console.error('Failed to parse user', e);
            }
        }
        setIsLoading(false);
    }, []);

    const getRoleDashboard = (role: string): string => {
        switch (role) {
            case 'doctor': return '/doctor';
            case 'nurse': return '/nurse';
            case 'patient': return '/patient';
            case 'finance': return '/finance';
            case 'admin': return '/admin';
            default: return '/dashboard';
        }
    };

    const login = async (credentials: { username: string; password: string }) => {
        const formData = new URLSearchParams();
        formData.append('username', credentials.username);
        formData.append('password', credentials.password);
        
        const response = await fetch('http://localhost:8000/auth/token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: formData.toString(),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Invalid credentials');
        }

        const data = await response.json();
        localStorage.setItem('access_token', data.access_token);
        
        const payload = JSON.parse(atob(data.access_token.split('.')[1]));
        const userData: User = {
            id: payload.id,
            email: payload.sub,
            full_name: payload.sub?.split('@')[0] || 'User',
            role: payload.role,
        };
        
        setUser(userData);
        localStorage.setItem('user', JSON.stringify(userData));
        
        // Redirect to role-specific dashboard
        const dashboardPath = getRoleDashboard(userData.role);
        router.push(dashboardPath);
    };

    const logout = () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        setUser(null);
        router.push('/login');
    };

    return React.createElement(
        AuthContext.Provider,
        { value: { user, isLoading, login, logout, isAuthenticated: !!user } },
        children
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within AuthProvider');
    }
    return context;
}