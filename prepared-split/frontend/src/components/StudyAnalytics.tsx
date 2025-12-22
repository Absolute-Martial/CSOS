'use client'

import { useEffect, useState } from 'react'

interface DailyStats {
    date: string
    total_duration: number
    session_count: number
    deep_work_count: number
    points_earned: number
}

interface HourlyProductivity {
    hour: number
    total_minutes: number
    session_count: number
    avg_duration_minutes: number
}

interface SubjectStats {
    subject_id: number
    subject_code: string
    subject_name: string
    color: string
    total_duration: number
    session_count: number
    deep_work_count: number
    avg_session_minutes: number
}

interface Analytics {
    period: {
        days: number
        start_date: string
        end_date: string
    }
    totals: {
        total_sessions: number
        total_duration_seconds: number
        total_points: number
        deep_work_sessions: number
        deep_work_hours: number
        avg_session_minutes: number
    }
    daily_stats: DailyStats[]
    by_subject: SubjectStats[]
    hourly_productivity: HourlyProductivity[]
}

export default function StudyAnalytics() {
    const [analytics, setAnalytics] = useState<Analytics | null>(null)
    const [loading, setLoading] = useState(true)
    const [period, setPeriod] = useState(7)

    useEffect(() => {
        fetchAnalytics()
    }, [period])

    const fetchAnalytics = async () => {
        setLoading(true)
        try {
            const res = await fetch(`/api/timer/analytics?days=${period}`)
            if (res.ok) {
                const data = await res.json()
                setAnalytics(data)
            }
        } catch (error) {
            console.error('Failed to fetch analytics:', error)
        } finally {
            setLoading(false)
        }
    }

    const formatDuration = (seconds: number) => {
        const hours = Math.floor(seconds / 3600)
        const minutes = Math.floor((seconds % 3600) / 60)
        if (hours > 0) {
            return `${hours}h ${minutes}m`
        }
        return `${minutes}m`
    }

    const getMaxDuration = () => {
        if (!analytics?.daily_stats.length) return 1
        return Math.max(...analytics.daily_stats.map(d => d.total_duration)) || 1
    }

    if (loading) {
        return (
            <div className="glass rounded-2xl p-6">
                <div className="animate-pulse space-y-4">
                    <div className="h-6 bg-zinc-700 rounded w-1/3"></div>
                    <div className="h-40 bg-zinc-700 rounded"></div>
                </div>
            </div>
        )
    }

    if (!analytics) {
        return (
            <div className="glass rounded-2xl p-6">
                <p className="text-zinc-400">Failed to load analytics</p>
            </div>
        )
    }

    return (
        <div className="space-y-6">
            {/* Header with Period Selector */}
            <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold text-white">Study Analytics</h2>
                <div className="flex gap-2">
                    {[7, 14, 30].map(days => (
                        <button
                            key={days}
                            onClick={() => setPeriod(days)}
                            className={`px-3 py-1 rounded-lg text-sm transition-colors ${
                                period === days
                                    ? 'bg-primary text-white'
                                    : 'bg-surface-light text-zinc-400 hover:text-white'
                            }`}
                        >
                            {days}d
                        </button>
                    ))}
                </div>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="glass rounded-xl p-4">
                    <p className="text-3xl font-bold text-white">
                        {formatDuration(analytics.totals.total_duration_seconds)}
                    </p>
                    <p className="text-sm text-zinc-400">Total Study Time</p>
                </div>
                <div className="glass rounded-xl p-4">
                    <p className="text-3xl font-bold text-primary">
                        {analytics.totals.total_sessions}
                    </p>
                    <p className="text-sm text-zinc-400">Sessions</p>
                </div>
                <div className="glass rounded-xl p-4">
                    <p className="text-3xl font-bold text-green-400">
                        {analytics.totals.deep_work_sessions}
                    </p>
                    <p className="text-sm text-zinc-400">Deep Work Sessions</p>
                </div>
                <div className="glass rounded-xl p-4">
                    <p className="text-3xl font-bold text-yellow-400">
                        {analytics.totals.total_points}
                    </p>
                    <p className="text-sm text-zinc-400">Points Earned</p>
                </div>
            </div>

            {/* Daily Activity Chart */}
            <div className="glass rounded-2xl p-6">
                <h3 className="text-lg font-semibold text-white mb-4">Daily Activity</h3>
                <div className="flex items-end gap-1 h-32">
                    {analytics.daily_stats.map((day, i) => {
                        const height = (day.total_duration / getMaxDuration()) * 100
                        const date = new Date(day.date)
                        const dayName = date.toLocaleDateString('en-US', { weekday: 'short' })

                        return (
                            <div key={i} className="flex-1 flex flex-col items-center gap-1">
                                <div
                                    className={`w-full rounded-t transition-all ${
                                        day.deep_work_count > 0
                                            ? 'bg-gradient-to-t from-primary to-green-400'
                                            : 'bg-primary/60'
                                    }`}
                                    style={{ height: `${Math.max(height, 4)}%` }}
                                    title={`${formatDuration(day.total_duration)} - ${day.session_count} sessions`}
                                />
                                <span className="text-xs text-zinc-500">{dayName}</span>
                            </div>
                        )
                    })}
                </div>
                <div className="flex justify-between mt-2 text-xs text-zinc-500">
                    <span>0h</span>
                    <span>{formatDuration(getMaxDuration())}</span>
                </div>
            </div>

            {/* Subject Breakdown */}
            {analytics.by_subject.length > 0 && (
                <div className="glass rounded-2xl p-6">
                    <h3 className="text-lg font-semibold text-white mb-4">By Subject</h3>
                    <div className="space-y-3">
                        {analytics.by_subject.map(subject => {
                            const totalSeconds = analytics.totals.total_duration_seconds || 1
                            const percentage = (subject.total_duration / totalSeconds) * 100

                            return (
                                <div key={subject.subject_id} className="space-y-1">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-2">
                                            <div
                                                className="w-3 h-3 rounded-full"
                                                style={{ backgroundColor: subject.color }}
                                            />
                                            <span className="text-sm font-medium text-white">
                                                {subject.subject_code}
                                            </span>
                                            <span className="text-xs text-zinc-500">
                                                {subject.subject_name}
                                            </span>
                                        </div>
                                        <span className="text-sm text-zinc-400">
                                            {formatDuration(subject.total_duration)}
                                        </span>
                                    </div>
                                    <div className="h-2 bg-surface-light rounded-full overflow-hidden">
                                        <div
                                            className="h-full rounded-full transition-all"
                                            style={{
                                                width: `${percentage}%`,
                                                backgroundColor: subject.color
                                            }}
                                        />
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                </div>
            )}

            {/* Hourly Productivity */}
            {analytics.hourly_productivity.length > 0 && (
                <div className="glass rounded-2xl p-6">
                    <h3 className="text-lg font-semibold text-white mb-4">Peak Hours</h3>
                    <div className="grid grid-cols-12 gap-1">
                        {Array.from({ length: 24 }, (_, hour) => {
                            const data = analytics.hourly_productivity.find(h => h.hour === hour)
                            const maxMinutes = Math.max(
                                ...analytics.hourly_productivity.map(h => h.total_minutes)
                            ) || 1
                            const intensity = data ? data.total_minutes / maxMinutes : 0

                            return (
                                <div
                                    key={hour}
                                    className="aspect-square rounded"
                                    style={{
                                        backgroundColor: intensity > 0
                                            ? `rgba(99, 102, 241, ${0.2 + intensity * 0.8})`
                                            : 'rgba(255, 255, 255, 0.05)'
                                    }}
                                    title={`${hour}:00 - ${data?.total_minutes || 0} minutes`}
                                />
                            )
                        })}
                    </div>
                    <div className="flex justify-between mt-2 text-xs text-zinc-500">
                        <span>12 AM</span>
                        <span>12 PM</span>
                        <span>11 PM</span>
                    </div>
                </div>
            )}
        </div>
    )
}
