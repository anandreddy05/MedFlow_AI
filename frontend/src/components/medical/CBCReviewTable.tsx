// src/components/medical/CBCReviewTable.tsx
'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { 
    Edit2, 
    Check, 
    X, 
    AlertTriangle, 
    TrendingUp, 
    TrendingDown,
    Save
} from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface CBCResult {
    test_name: string;
    value: number;
    unit: string;
    reference_range_min: number | null;
    reference_range_max: number | null;
    flag: 'Normal' | 'High' | 'Low';
    confidence?: number;
}

interface CBCReviewTableProps {
    data: {
        patient_name?: string;
        collection_date?: string;
        results: CBCResult[];
    };
    onDataChange: (data: any) => void;
}

export function CBCReviewTable({ data, onDataChange }: CBCReviewTableProps) {
    const [editingCell, setEditingCell] = useState<{ row: number; field: string } | null>(null);
    const [editValue, setEditValue] = useState<string>('');
    const [localData, setLocalData] = useState(data);

    const handleEdit = (rowIndex: number, field: string, currentValue: any) => {
        setEditingCell({ row: rowIndex, field });
        setEditValue(String(currentValue));
    };

    const handleSave = (rowIndex: number, field: string) => {
        const newResults = [...localData.results];
        let parsedValue: any = editValue;
        
        if (field === 'value') {
            parsedValue = parseFloat(editValue);
        }
        
        newResults[rowIndex] = { ...newResults[rowIndex], [field]: parsedValue };
        
        // Update flag based on new value
        if (field === 'value') {
            const result = newResults[rowIndex];
            const isHigh = result.reference_range_max && parsedValue > result.reference_range_max;
            const isLow = result.reference_range_min && parsedValue < result.reference_range_min;
            newResults[rowIndex].flag = isHigh ? 'High' : isLow ? 'Low' : 'Normal';
        }
        
        const updatedData = { ...localData, results: newResults };
        setLocalData(updatedData);
        onDataChange(updatedData);
        setEditingCell(null);
    };

    const getFlagColor = (flag: string) => {
        switch(flag) {
            case 'High': return 'text-red-600 bg-red-50';
            case 'Low': return 'text-orange-600 bg-orange-50';
            default: return 'text-green-600 bg-green-50';
        }
    };

    const getFlagIcon = (flag: string) => {
        switch(flag) {
            case 'High': return <TrendingUp className="w-3 h-3" />;
            case 'Low': return <TrendingDown className="w-3 h-3" />;
            default: return <Check className="w-3 h-3" />;
        }
    };

    const getConfidenceColor = (confidence: number) => {
        if (confidence >= 0.9) return 'bg-green-100 text-green-700';
        if (confidence >= 0.7) return 'bg-yellow-100 text-yellow-700';
        return 'bg-red-100 text-red-700';
    };

    return (
        <div className="space-y-6">
            {/* Patient Info */}
            <div className="bg-gray-50 rounded-lg p-4">
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="text-sm text-gray-600">Patient Name</label>
                        <Input 
                            value={localData.patient_name || ''}
                            onChange={(e) => {
                                const updated = { ...localData, patient_name: e.target.value };
                                setLocalData(updated);
                                onDataChange(updated);
                            }}
                            className="mt-1"
                        />
                    </div>
                    <div>
                        <label className="text-sm text-gray-600">Collection Date</label>
                        <Input 
                            type="date"
                            value={localData.collection_date?.split('T')[0] || ''}
                            onChange={(e) => {
                                const updated = { ...localData, collection_date: e.target.value };
                                setLocalData(updated);
                                onDataChange(updated);
                            }}
                            className="mt-1"
                        />
                    </div>
                </div>
            </div>

            {/* Results Table */}
            <div className="overflow-x-auto rounded-lg border border-gray-200">
                <table className="w-full">
                    <thead className="bg-gray-50 border-b border-gray-200">
                        <tr>
                            <th className="text-left p-3 text-sm font-semibold text-gray-900">Test Name</th>
                            <th className="text-left p-3 text-sm font-semibold text-gray-900">Value</th>
                            <th className="text-left p-3 text-sm font-semibold text-gray-900">Unit</th>
                            <th className="text-left p-3 text-sm font-semibold text-gray-900">Reference Range</th>
                            <th className="text-left p-3 text-sm font-semibold text-gray-900">Status</th>
                            <th className="text-left p-3 text-sm font-semibold text-gray-900">Confidence</th>
                            <th className="text-left p-3 text-sm font-semibold text-gray-900"></th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                        {localData.results?.map((result, idx) => (
                            <motion.tr 
                                key={idx}
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                transition={{ delay: idx * 0.02 }}
                                className={`hover:bg-gray-50 transition-colors ${
                                    result.flag !== 'Normal' ? 'bg-red-50/30' : ''
                                }`}
                            >
                                <td className="p-3 text-sm font-medium text-gray-900">
                                    {result.test_name}
                                </td>
                                <td className="p-3">
                                    {editingCell?.row === idx && editingCell?.field === 'value' ? (
                                        <div className="flex items-center gap-2">
                                            <Input
                                                type="number"
                                                value={editValue}
                                                onChange={(e) => setEditValue(e.target.value)}
                                                className="w-24 h-8 text-sm"
                                                autoFocus
                                            />
                                            <Button size="sm" variant="ghost" onClick={() => handleSave(idx, 'value')}>
                                                <Check className="w-3 h-3" />
                                            </Button>
                                            <Button size="sm" variant="ghost" onClick={() => setEditingCell(null)}>
                                                <X className="w-3 h-3" />
                                            </Button>
                                        </div>
                                    ) : (
                                        <div 
                                            className={`flex items-center gap-2 cursor-pointer group ${result.flag !== 'Normal' ? 'font-semibold' : ''}`}
                                            onClick={() => handleEdit(idx, 'value', result.value)}
                                        >
                                            <span className={result.flag === 'High' ? 'text-red-600' : result.flag === 'Low' ? 'text-orange-600' : ''}>
                                                {result.value}
                                            </span>
                                            <Edit2 className="w-3 h-3 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                                        </div>
                                    )}
                                </td>
                                <td className="p-3 text-sm text-gray-600">{result.unit}</td>
                                <td className="p-3 text-sm text-gray-600">
                                    {result.reference_range_min} - {result.reference_range_max}
                                </td>
                                <td className="p-3">
                                    <Badge className={`gap-1 ${getFlagColor(result.flag)}`}>
                                        {getFlagIcon(result.flag)}
                                        {result.flag}
                                    </Badge>
                                </td>
                                <td className="p-3">
                                    <div className="flex items-center gap-2">
                                        <div className="w-16 bg-gray-200 rounded-full h-1.5">
                                            <div 
                                                className={`h-1.5 rounded-full ${
                                                    (result.confidence || 0.95) >= 0.9 ? 'bg-green-500' :
                                                    (result.confidence || 0.95) >= 0.7 ? 'bg-yellow-500' : 'bg-red-500'
                                                }`}
                                                style={{ width: `${(result.confidence || 0.95) * 100}%` }}
                                            />
                                        </div>
                                        <span className="text-xs text-gray-500">
                                            {Math.round((result.confidence || 0.95) * 100)}%
                                        </span>
                                    </div>
                                </td>
                                <td className="p-3">
                                    <Button size="sm" variant="ghost">
                                        <Save className="w-3 h-3" />
                                    </Button>
                                </td>
                            </motion.tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Summary Statistics */}
            <div className="bg-blue-50 rounded-lg p-4">
                <h4 className="font-medium text-blue-900 mb-2">Clinical Summary</h4>
                <div className="flex gap-4 text-sm">
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                        <span>Normal: {localData.results?.filter(r => r.flag === 'Normal').length}</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                        <span>High: {localData.results?.filter(r => r.flag === 'High').length}</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 bg-orange-500 rounded-full"></div>
                        <span>Low: {localData.results?.filter(r => r.flag === 'Low').length}</span>
                    </div>
                </div>
            </div>
        </div>
    );
}