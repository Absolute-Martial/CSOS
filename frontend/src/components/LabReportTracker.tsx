'use client'

import { useEffect, useState } from 'react'

interface LabReport {
    id: number
    experiment_name: string
    subject_code: string
    subject_name: string
    color: string
    lab_date: string
    due_date: string
    status: string
    days_remaining: number
    urgency: string
    notes?: string
}

export default function LabReportTracker() {
    const [reports, setReports] = useState<LabReport[]>([])
    const [loading, setLoading] = useState(true)
    const [showAddModal, setShowAddModal] = useState(false)

    // Form state
    const [newReport, setNewReport] = useState({
        subject_code: '',
        experiment_name: '',
        due_date: '',
        lab_date: ''
    })
    const [submitting, setSubmitting] = useState(false)

    useEffect(() => {
        fetchReports()
    }, [])

    const fetchReports = async () => {
        try {
            const res = await fetch('/api/labs/countdown')
            if (res.ok) {
                const data = await res.json()
                setReports(data.reports || [])
            }
        } catch (error) {
            console.error('Failed to fetch lab reports:', error)
        } finally {
            setLoading(false)
        }
    }

    const addReport = async () => {
        if (!newReport.subject_code || !newReport.experiment_name || !newReport.due_date) return
        setSubmitting(true)

        try {
            const formData = new FormData()
            formData.append('subject_code', newReport.subject_code)
            formData.append('experiment_name', newReport.experiment_name)
            formData.append('due_date', newReport.due_date)
            if (newReport.lab_date) {
                formData.append('lab_date', newReport.lab_date)
            }

            const res = await fetch('/api/labs/track', {
                method: 'POST',
                body: formData
            })

            if (res.ok) {
                await fetchReports()
                setShowAddModal(false)
                setNewReport({ subject_code: '', experiment_name: '', due_date: '', lab_date: '' })
            }
        } catch (error) {
            console.error('Failed to add report:', error)
        } finally {
            setSubmitting(false)
        }
    }

    const updateStatus = async (reportId: number, newStatus: string) => {
        try {
            const formData = new FormData()
            formData.append('status', newStatus)

            const res = await fetch(`/api/labs/${reportId}/status`, {
                method: 'PATCH',
                body: formData
            })

            if (res.ok) {
                await fetchReports()
            }
        } catch (error) {
            console.error('Failed to update status:', error)
        }
    }

    const getUrgencyStyles = (urgency: string) => {
        switch (urgency) {
            case 'overdue':
                return {
                    bg: 'bg-red-500/20',
                    border: 'border-red-500/30',
                    text: 'text-red-400',
                    badge: 'bg-red-500'
                }
            case 'urgent':
                return {
                    bg: 'bg-orange-500/20',
                    border: 'border-orange-500/30',
                    text: 'text-orange-400',
                    badge: 'bg-orange-500'
                }
            case 'soon':
                return {
                    bg: 'bg-yellow-500/20',
                    border: 'border-yellow-500/30',
                    text: 'text-yellow-400',
                    badge: 'bg-yellow-500'
                }
            default:
                return {
                    bg: 'bg-zinc-500/10',
                    border: 'border-zinc-500/20',
                    text: 'text-zinc-400',
                    badge: 'bg-zinc-500'
                }
        }
    }

    const statusOptions = [
        { value: 'pending', label: 'Not Started', icon: '⏳' },
        { value: 'in_progress', label: 'In Progress', icon: '✏️' },
        { value: 'draft_complete', label: 'Draft Done', icon: '📄' },
        { value: 'submitted', label: 'Submitted', icon: '✅' }
    ]

    if (loading) {
        return (
            <div className="glass rounded-2xl p-6">
                <div className="animate-pulse space-y-4">
                    <div className="h-6 bg-zinc-700 rounded w-1/3"></div>
                    <div className="space-y-3">
                        {[1, 2, 3].map(i => (
                            <div key={i} className="h-24 bg-zinc-700 rounded-xl"></div>
                        ))}
                    </div>
                </div>
            </div>
        )
    }

    const urgentCount = reports.filter(r => r.urgency === 'overdue' || r.urgency === 'urgent').length

    return (
        <div className="glass rounded-2xl p-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h2 className="text-xl font-bold text-white flex items-center gap-2">
                        <span>🧪</span> Lab Reports
                    </h2>
                    {urgentCount > 0 && (
                        <p className="text-sm text-red-400 mt-1">
                            {urgentCount} urgent report{urgentCount > 1 ? 's' : ''}
                        </p>
                    )}
                </div>
                <button
                    onClick={() => setShowAddModal(true)}
                    className="px-4 py-2 rounded-lg bg-primary/20 hover:bg-primary/30 text-primary transition-colors"
                >
                    + Track New
                </button>
            </div>

            {/* Reports List */}
            {reports.length === 0 ? (
                <div className="text-center py-8">
                    <p className="text-zinc-400 mb-4">No lab reports being tracked</p>
                    <button
                        onClick={() => setShowAddModal(true)}
                        className="text-primary hover:underline"
                    >
                        Add your first lab report
                    </button>
                </div>
            ) : (
                <div className="space-y-4">
                    {reports.map(report => {
                        const styles = getUrgencyStyles(report.urgency)
                        const currentStatus = statusOptions.find(s => s.value === report.status)

                        return (
                            <div
                                key={report.id}
                                className={`p-4 rounded-xl border ${styles.bg} ${styles.border}`}
                            >
                                <div className="flex items-start justify-between mb-3">
                                    <div>
                                        <div className="flex items-center gap-2 mb-1">
                                            <span
                                                className="text-xs px-2 py-0.5 rounded text-white"
                                                style={{ backgroundColor: report.color }}
                                            >
                                                {report.subject_code}
                                            </span>
                                            <span className="text-xs text-zinc-500">{report.subject_name}</span>
                                        </div>
                                        <h3 className="font-medium text-white">{report.experiment_name}</h3>
                                    </div>

                                    {/* Countdown */}
                                    <div className={`text-right ${styles.text}`}>
                                        {report.days_remaining < 0 ? (
                                            <>
                                                <p className="text-2xl font-bold">{Math.abs(report.days_remaining)}</p>
                                                <p className="text-xs">days overdue</p>
                                            </>
                                        ) : report.days_remaining === 0 ? (
                                            <>
                                                <p className="text-2xl font-bold">TODAY</p>
                                                <p className="text-xs">due date</p>
                                            </>
                                        ) : (
                                            <>
                                                <p className="text-2xl font-bold">{report.days_remaining}</p>
                                                <p className="text-xs">days left</p>
                                            </>
                                        )}
                                    </div>
                                </div>

                                {/* Status Selector */}
                                <div className="flex items-center gap-2">
                                    {statusOptions.map(opt => (
                                        <button
                                            key={opt.value}
                                            onClick={() => updateStatus(report.id, opt.value)}
                                            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                                                report.status === opt.value
                                                    ? 'bg-primary text-white'
                                                    : 'bg-surface text-zinc-400 hover:text-white'
                                            }`}
                                        >
                                            <span>{opt.icon}</span>
                                            <span className="hidden sm:inline">{opt.label}</span>
                                        </button>
                                    ))}
                                </div>

                                {/* Dates */}
                                <div className="flex gap-4 mt-3 text-xs text-zinc-500">
                                    {report.lab_date && (
                                        <span>Lab: {new Date(report.lab_date).toLocaleDateString()}</span>
                                    )}
                                    <span>Due: {new Date(report.due_date).toLocaleDateString()}</span>
                                </div>
                            </div>
                        )
                    })}
                </div>
            )}

            {/* Add Modal */}
            {showAddModal && (
                <>
                    <div
                        className="fixed inset-0 bg-black/50 z-50"
                        onClick={() => setShowAddModal(false)}
                    />
                    <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md glass rounded-2xl p-6 z-50">
                        <h3 className="text-lg font-bold text-white mb-4">Track Lab Report</h3>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm text-zinc-400 mb-1">Subject Code *</label>
                                <input
                                    type="text"
                                    value={newReport.subject_code}
                                    onChange={(e) => setNewReport({ ...newReport, subject_code: e.target.value.toUpperCase() })}
                                    placeholder="PHYS102"
                                    className="w-full px-4 py-2 rounded-lg bg-surface border border-white/10 text-white placeholder-zinc-500 focus:outline-none focus:border-primary uppercase"
                                />
                            </div>

                            <div>
                                <label className="block text-sm text-zinc-400 mb-1">Experiment Name *</label>
                                <input
                                    type="text"
                                    value={newReport.experiment_name}
                                    onChange={(e) => setNewReport({ ...newReport, experiment_name: e.target.value })}
                                    placeholder="Simple Pendulum"
                                    className="w-full px-4 py-2 rounded-lg bg-surface border border-white/10 text-white placeholder-zinc-500 focus:outline-none focus:border-primary"
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm text-zinc-400 mb-1">Lab Date</label>
                                    <input
                                        type="date"
                                        value={newReport.lab_date}
                                        onChange={(e) => setNewReport({ ...newReport, lab_date: e.target.value })}
                                        className="w-full px-4 py-2 rounded-lg bg-surface border border-white/10 text-white focus:outline-none focus:border-primary"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm text-zinc-400 mb-1">Due Date *</label>
                                    <input
                                        type="date"
                                        value={newReport.due_date}
                                        onChange={(e) => setNewReport({ ...newReport, due_date: e.target.value })}
                                        className="w-full px-4 py-2 rounded-lg bg-surface border border-white/10 text-white focus:outline-none focus:border-primary"
                                    />
                                </div>
                            </div>
                        </div>

                        <div className="flex gap-3 mt-6">
                            <button
                                onClick={() => setShowAddModal(false)}
                                className="flex-1 py-2 rounded-lg bg-surface-light text-zinc-400 hover:text-white transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={addReport}
                                disabled={!newReport.subject_code || !newReport.experiment_name || !newReport.due_date || submitting}
                                className="flex-1 py-2 rounded-lg bg-primary text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {submitting ? 'Adding...' : 'Add Report'}
                            </button>
                        </div>
                    </div>
                </>
            )}
        </div>
    )
}
