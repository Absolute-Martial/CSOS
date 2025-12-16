'use client'

import { useEffect, useState, useCallback } from 'react'

interface TimerStatus {
    running: boolean
    session_id?: number
    elapsed_seconds?: number
    subject_code?: string
    subject_name?: string
    color?: string
    title?: string
    started_at?: string
}

interface Subject {
    id: number
    code: string
    name: string
    color: string
}

export default function StudyTimer() {
    const [status, setStatus] = useState<TimerStatus>({ running: false })
    const [subjects, setSubjects] = useState<Subject[]>([])
    const [selectedSubject, setSelectedSubject] = useState<number | null>(null)
    const [elapsed, setElapsed] = useState(0)
    const [showDropdown, setShowDropdown] = useState(false)
    const [loading, setLoading] = useState(false)

    // Fetch timer status on mount
    useEffect(() => {
        fetchStatus()
        fetchSubjects()
        const interval = setInterval(fetchStatus, 30000) // Refresh every 30s
        return () => clearInterval(interval)
    }, [])

    // Update elapsed time every second when running
    useEffect(() => {
        if (!status.running) {
            setElapsed(0)
            return
        }

        setElapsed(status.elapsed_seconds || 0)
        const interval = setInterval(() => {
            setElapsed(prev => prev + 1)
        }, 1000)

        return () => clearInterval(interval)
    }, [status.running, status.elapsed_seconds])

    const fetchStatus = async () => {
        try {
            const res = await fetch('/api/timer/status')
            if (res.ok) {
                const data = await res.json()
                setStatus(data)
            }
        } catch (error) {
            console.error('Failed to fetch timer status:', error)
        }
    }

    const fetchSubjects = async () => {
        try {
            const res = await fetch('/api/subjects')
            if (res.ok) {
                const data = await res.json()
                setSubjects(data)
            }
        } catch (error) {
            console.error('Failed to fetch subjects:', error)
        }
    }

    const startTimer = async (subjectId?: number) => {
        setLoading(true)
        try {
            const params = new URLSearchParams()
            if (subjectId) params.append('subject_id', subjectId.toString())

            const res = await fetch(`/api/timer/start?${params}`, { method: 'POST' })
            if (res.ok) {
                await fetchStatus()
                setShowDropdown(false)
            }
        } catch (error) {
            console.error('Failed to start timer:', error)
        } finally {
            setLoading(false)
        }
    }

    const stopTimer = async () => {
        setLoading(true)
        try {
            const res = await fetch('/api/timer/stop', { method: 'POST' })
            if (res.ok) {
                const data = await res.json()
                await fetchStatus()
                // Show completion message
                if (data.points_earned > 0) {
                    console.log(`Earned ${data.points_earned} points!`)
                }
            }
        } catch (error) {
            console.error('Failed to stop timer:', error)
        } finally {
            setLoading(false)
        }
    }

    const formatTime = (seconds: number) => {
        const hrs = Math.floor(seconds / 3600)
        const mins = Math.floor((seconds % 3600) / 60)
        const secs = seconds % 60
        if (hrs > 0) {
            return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
        }
        return `${mins}:${secs.toString().padStart(2, '0')}`
    }

    const isDeepWork = elapsed >= 5400 // 90 minutes

    if (status.running) {
        return (
            <div className="flex items-center gap-3">
                {/* Timer Display */}
                <div
                    className={`flex items-center gap-3 px-4 py-2 rounded-lg ${isDeepWork ? 'bg-green-500/20 border border-green-500/30' : 'bg-primary/20 border border-primary/30'
                        } transition-all`}
                >
                    {/* Pulsing indicator */}
                    <div className={`w-2 h-2 rounded-full ${isDeepWork ? 'bg-green-400' : 'bg-primary'} animate-pulse`} />

                    {/* Subject badge */}
                    {status.subject_code && (
                        <span
                            className="text-sm font-medium px-2 py-0.5 rounded"
                            style={{ backgroundColor: status.color || '#6366f1', color: 'white' }}
                        >
                            {status.subject_code}
                        </span>
                    )}

                    {/* Time */}
                    <span className={`font-mono text-lg font-bold ${isDeepWork ? 'text-green-400' : 'text-white'}`}>
                        {formatTime(elapsed)}
                    </span>

                    {/* Deep Work badge */}
                    {isDeepWork && (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-green-500/30 text-green-300">
                            Deep Work
                        </span>
                    )}
                </div>

                {/* Stop Button */}
                <button
                    onClick={stopTimer}
                    disabled={loading}
                    className="p-2 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-400 transition-colors disabled:opacity-50"
                    title="Stop Timer"
                >
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                        <rect x="6" y="6" width="8" height="8" rx="1" />
                    </svg>
                </button>
            </div>
        )
    }

    return (
        <div className="relative">
            {/* Start Button with Dropdown */}
            <button
                onClick={() => setShowDropdown(!showDropdown)}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-surface-light hover:bg-surface transition-colors disabled:opacity-50"
            >
                <svg className="w-5 h-5 text-primary" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
                </svg>
                <span className="text-sm font-medium text-white">Start Timer</span>
            </button>

            {/* Dropdown */}
            {showDropdown && (
                <div className="absolute top-full right-0 mt-2 w-56 rounded-lg bg-surface border border-white/10 shadow-xl z-50">
                    <div className="p-2">
                        {/* Quick start without subject */}
                        <button
                            onClick={() => startTimer()}
                            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-surface-light transition-colors text-left"
                        >
                            <div className="w-3 h-3 rounded-full bg-zinc-500" />
                            <span className="text-sm text-white">General Study</span>
                        </button>

                        {/* Subject options */}
                        {subjects.map(subject => (
                            <button
                                key={subject.id}
                                onClick={() => startTimer(subject.id)}
                                className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-surface-light transition-colors text-left"
                            >
                                <div
                                    className="w-3 h-3 rounded-full"
                                    style={{ backgroundColor: subject.color }}
                                />
                                <div>
                                    <span className="text-sm font-medium text-white">{subject.code}</span>
                                    <span className="text-xs text-zinc-400 ml-2">{subject.name}</span>
                                </div>
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Click outside to close */}
            {showDropdown && (
                <div
                    className="fixed inset-0 z-40"
                    onClick={() => setShowDropdown(false)}
                />
            )}
        </div>
    )
}
