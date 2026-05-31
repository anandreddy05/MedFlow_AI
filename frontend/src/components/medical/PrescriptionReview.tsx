// src/components/medical/PrescriptionReview.tsx
'use client';

import { useState } from 'react';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Plus, Trash2 } from 'lucide-react';

interface Medication {
    medicine_name: string;
    dosage: string;
    timing: 'morning' | 'afternoon' | 'evening' | 'night';
    food_instruction: 'before_food' | 'after_food' | 'with_food' | 'independent';
    frequency: 'daily' | 'weekly' | 'as_needed';
}

interface PrescriptionReviewProps {
    data: {
        clinical_notes?: string;
        medications: Medication[];
    };
    onDataChange: (data: any) => void;
}

export function PrescriptionReview({ data, onDataChange }: PrescriptionReviewProps) {
    const [localData, setLocalData] = useState(data);

    const updateMedication = (index: number, field: keyof Medication, value: string) => {
        const newMedications = [...localData.medications];
        newMedications[index] = { ...newMedications[index], [field]: value };
        const updated = { ...localData, medications: newMedications };
        setLocalData(updated);
        onDataChange(updated);
    };

    const addMedication = () => {
        const newMedication: Medication = {
            medicine_name: '',
            dosage: '',
            timing: 'morning',
            food_instruction: 'with_food',
            frequency: 'daily',
        };
        const updated = { ...localData, medications: [...localData.medications, newMedication] };
        setLocalData(updated);
        onDataChange(updated);
    };

    const removeMedication = (index: number) => {
        const newMedications = localData.medications.filter((_, i) => i !== index);
        const updated = { ...localData, medications: newMedications };
        setLocalData(updated);
        onDataChange(updated);
    };

    return (
        <div className="space-y-6">
            <div>
                <label className="text-sm font-medium text-gray-700">Clinical Notes</label>
                <Textarea
                    value={localData.clinical_notes || ''}
                    onChange={(e) => {
                        const updated = { ...localData, clinical_notes: e.target.value };
                        setLocalData(updated);
                        onDataChange(updated);
                    }}
                    rows={4}
                    className="mt-1"
                    placeholder="Enter clinical notes and instructions..."
                />
            </div>

            <div>
                <div className="flex items-center justify-between mb-3">
                    <label className="text-sm font-medium text-gray-700">Medications</label>
                    <Button size="sm" onClick={addMedication} variant="outline">
                        <Plus className="w-4 h-4 mr-1" />
                        Add Medication
                    </Button>
                </div>

                <div className="space-y-4">
                    {localData.medications.map((med, idx) => (
                        <div key={idx} className="border border-gray-200 rounded-lg p-4">
                            <div className="grid grid-cols-2 gap-3 mb-3">
                                <div>
                                    <label className="text-xs text-gray-500">Medicine Name</label>
                                    <Input
                                        value={med.medicine_name}
                                        onChange={(e) => updateMedication(idx, 'medicine_name', e.target.value)}
                                        className="mt-1"
                                    />
                                </div>
                                <div>
                                    <label className="text-xs text-gray-500">Dosage</label>
                                    <Input
                                        value={med.dosage}
                                        onChange={(e) => updateMedication(idx, 'dosage', e.target.value)}
                                        className="mt-1"
                                        placeholder="e.g., 500mg"
                                    />
                                </div>
                            </div>
                            <div className="grid grid-cols-3 gap-3">
                                <div>
                                    <label className="text-xs text-gray-500">Timing</label>
                                    <select
                                        value={med.timing}
                                        onChange={(e) => updateMedication(idx, 'timing', e.target.value as any)}
                                        className="mt-1 w-full rounded-md border border-gray-300 p-2 text-sm"
                                    >
                                        <option value="morning">Morning</option>
                                        <option value="afternoon">Afternoon</option>
                                        <option value="evening">Evening</option>
                                        <option value="night">Night</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="text-xs text-gray-500">With Food</label>
                                    <select
                                        value={med.food_instruction}
                                        onChange={(e) => updateMedication(idx, 'food_instruction', e.target.value as any)}
                                        className="mt-1 w-full rounded-md border border-gray-300 p-2 text-sm"
                                    >
                                        <option value="before_food">Before Food</option>
                                        <option value="after_food">After Food</option>
                                        <option value="with_food">With Food</option>
                                        <option value="independent">Independent</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="text-xs text-gray-500">Frequency</label>
                                    <select
                                        value={med.frequency}
                                        onChange={(e) => updateMedication(idx, 'frequency', e.target.value as any)}
                                        className="mt-1 w-full rounded-md border border-gray-300 p-2 text-sm"
                                    >
                                        <option value="daily">Daily</option>
                                        <option value="weekly">Weekly</option>
                                        <option value="as_needed">As Needed</option>
                                    </select>
                                </div>
                            </div>
                            <div className="mt-3 flex justify-end">
                                <Button size="sm" variant="ghost" onClick={() => removeMedication(idx)}>
                                    <Trash2 className="w-4 h-4 text-red-500" />
                                </Button>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}