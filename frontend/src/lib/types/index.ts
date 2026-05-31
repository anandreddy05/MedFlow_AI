// src/lib/types/index.ts
export interface User {
    id: number;
    email: string;
    full_name: string;
    role: 'patient' | 'doctor' | 'nurse' | 'finance' | 'admin';
    is_active: boolean;
    must_change_password?: boolean;
}

export interface MedicalDocument {
    document_id: string;
    patient_id: string;
    report_type: 'cbc' | 'digital_prescription' | 'discharge_summary' | 'medical_invoice';
    extracted_data: any;
    content_markdown: string;
    approval_status: 'pending' | 'approved' | 'rejected';
    created_at: string;
    reviewed_by?: number;
    reviewed_at?: string;
}

export interface CBCReport {
    patient_name: string;
    collection_date: string;
    results: CBCResult[];
}

export interface CBCResult {
    test_name: string;
    value: number;
    unit: string;
    reference_range_min: number | null;
    reference_range_max: number | null;
    flag: 'Normal' | 'High' | 'Low';
    confidence?: number;
}