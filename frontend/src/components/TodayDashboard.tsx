'use client'

import { useEffect, useState } from 'react'

interface TimetableClass {
    start: string
    end: string
    subject: string
    type: string
    room: string
}

interface Gap {
    start: string
    end: string
    duration_mins: number
    is_deep_work_suitable: boolean
}

interface Task {
    id: number
    title: string
    subject_code?: string
    color?: string
    scheduled_start: string
    duration_mins: number
    status: string
    is_deep_work: boolean
}

interface LabReport {
    id: number
    experiment_name: string
    subject_code: string
    color: string
    due_date: string
    days_remaining: number
    urgency: string
    status: string
}

interface Deadline {
    type: string
    title: string
    subject_code?: string
    color?: string
    due_date: string
    days_remaining: number
}

interface TodayData {
    date: string
    day: string
    timetable: {
        classes: TimetableClass[]
        class_count: number
        next_class: TimetableClass | null
    }
    tasks: {
        scheduled: Task[]
        count: number
        completed: number
    }
    gaps: {
        total_available_mins: number
        deep_work_mins: number
        slots: Gap[]
    }
    lab_reports: {
        urgent: LabReport[]
        total_pending: number
    }
    deadlines: Deadline[]
    study_today: {
        total_minutes: number
        sessions: number
        deep_work_sessions: number
    }
    active_timer: any
    streak: {
        current_streak: number
        total_points: number
    }
}

export default function TodayDashboard() {
    const [data, setData] = useState<TodayData | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetchTodayData()
        // Refresh every minute
        const interval = setInterval(fetchTodayData, 60000)
        return () => clearInterval(interval)
    }, [])

    const fetchTodayData = async () => {
        try {
            const res = await fetch('/api/schedule/today')
            if (res.ok) {
                const result = await res.json()
                setData(result)
            }
        } catch (error) {
            console.error('Failed to fetch today data:', error)
        } finally {
            setLoading(false)
        }
    }

    const formatTime = (timeStr: string) => {
        const [hours, mins] = timeStr.split(':')
        const h = parseInt(hours)
        const ampm = h >= 12 ? 'PM' : 'AM'
        const hour12 = h % 12 || 12
        return `${hour12}:${mins} ${ampm}`
    }

    const formatDuration = (mins: number) => {
        const hours = Math.floor(mins / 60)
        const minutes = mins % 60
        if (hours > 0) {
            return `${hours}h ${minutes}m`
        }
        return `${minutes}m`
    }

    const getUrgencyColor = (urgency: string) => {
        switch (urgency) {
            case 'overdue': return 'bg-red-500/20 text-red-400 border-red-500/30'
            case 'urgent': return 'bg-orange-500/20 text-orange-400 border-orange-500/30'
            case 'soon': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
            default: return 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30'
        }
    }

    if (loading) {
        return (
            <div className="space-y-6">
                <div className="animate-pulse">
                    <div className="h-8 bg-zinc-700 rounded w-1/3 mb-6"></div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {[1, 2, 3].map(i => (
                            <div key={i} className="h-32 bg-zinc-700 rounded-xl"></div>
                        ))}
                    </div>
                </div>
            </div>
        )
    }

    if (!data) {
        return (
            <div className="glass rounded-2xl p-6 text-center">
                <p className="text-zinc-400">Failed to load schedule</p>
            </div>
        )
    }

    const currentTime = new Date()
    const currentHour = currentTime.getHours()
    const currentMins = currentTime.getMinutes()

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white">Today at a Glance</h1>
                    <p className="text-zinc-400">{data.day}, {new Date(data.date).toLocaleDateString('en-US', { month: 'long', day: 'numeric' })}</p>
                </div>
                {data.streak && (
                    <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-orange-500/20">
                        <span className="text-2xl">🔥</span>
                        <div>
                            <p className="text-lg font-bold text-orange-400">{data.streak.current_streak}</p>
                            <p className="text-xs text-zinc-400">day streak</p>
                        </div>
                    </div>
                )}
            </div>

            {/* Quick Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="glass rounded-xl p-4">
                    <p className="text-3xl font-bold text-primary">{data.timetable.class_count}</p>
                    <p className="text-sm text-zinc-400">Classes Today</p>
                </div>
                <div className="glass rounded-xl p-4">
                    <p className="text-3xl font-bold text-green-400">{formatDuration(data.gaps.deep_work_mins)}</p>
                    <p className="text-sm text-zinc-400">Deep Work Available</p>
                </div>
                <div className="glass rounded-xl p-4">
                    <p className="text-3xl font-bold text-blue-400">{data.tasks.count}</p>
                    <p className="text-sm text-zinc-400">Tasks Scheduled</p>
                </div>
                <div className="glass rounded-xl p-4">
                    <p className="text-3xl font-bold text-yellow-400">{formatDuration(data.study_today.total_minutes)}</p>
                    <p className="text-sm text-zinc-400">Studied Today</p>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Timeline */}
                <div className="glass rounded-2xl p-6">
                    <h2 className="text-lg font-semibold text-white mb-4">Schedule</h2>

                    {/* KU Classes */}
                    <div className="space-y-2 mb-4">
                        <h3 className="text-sm font-medium text-zinc-400 uppercase tracking-wider">University Classes</h3>
                        {data.timetable.classes.length === 0 ? (
                            <p className="text-zinc-500 text-sm py-2">No classes today</p>
                        ) : (
                            data.timetable.classes.map((cls, i) => {
                                const [startH, startM] = cls.start.split(':').map(Number)
                                const [endH, endM] = cls.end.split(':').map(Number)
                                const isPast = currentHour > endH || (currentHour === endH && currentMins > endM)
                                const isCurrent = currentHour >= startH && currentHour < endH

                                return (
                                    <div
                                        key={i}
                                        className={`flex items-center gap-4 p-3 rounded-lg transition-colors ${
                                            isCurrent ? 'bg-primary/20 border border-primary/30' :
                                            isPast ? 'opacity-50' : 'bg-surface-light'
                                        }`}
                                    >
                                        <div className="text-sm text-zinc-400 w-24">
                                            {formatTime(cls.start)} - {formatTime(cls.end)}
                                        </div>
                                        <div className="flex-1">
                                            <span className="font-medium text-white">{cls.subject}</span>
                                            <span className="text-xs text-zinc-500 ml-2">({cls.type})</span>
                                        </div>
                                        <span className="text-xs text-zinc-500">{cls.room}</span>
                                        {isCurrent && (
                                            <span className="text-xs px-2 py-0.5 rounded-full bg-primary text-white">NOW</span>
                                        )}
                                    </div>
                                )
                            })
                        )}
                    </div>

                    {/* Deep Work Slots */}
                    <div className="space-y-2">
                        <h3 className="text-sm font-medium text-zinc-400 uppercase tracking-wider">Deep Work Opportunities</h3>
                        {data.gaps.slots.filter(g => g.is_deep_work_suitable).length === 0 ? (
                            <p className="text-zinc-500 text-sm py-2">No deep work slots available</p>
                        ) : (
                            data.gaps.slots
                                .filter(g => g.is_deep_work_suitable)
                                .map((gap, i) => (
                                    <div
                                        key={i}
                                        className="flex items-center gap-4 p-3 rounded-lg bg-green-500/10 border border-green-500/20"
                                    >
                                        <div className="w-2 h-2 rounded-full bg-green-400"></div>
                                        <div className="text-sm text-zinc-400">
                                            {formatTime(gap.start)} - {formatTime(gap.end)}
                                        </div>
                                        <div className="flex-1 text-green-400 font-medium">
                                            {formatDuration(gap.duration_mins)}
                                        </div>
                                        <span className="text-xs text-green-400/70">Deep Work</span>
                                    </div>
                                ))
                        )}
                    </div>
                </div>

                {/* Deadlines & Lab Reports */}
                <div className="space-y-6">
                    {/* Lab Reports */}
                    {data.lab_reports.total_pending > 0 && (
                        <div className="glass rounded-2xl p-6">
                            <div className="flex items-center justify-between mb-4">
                                <h2 className="text-lg font-semibold text-white">Lab Reports</h2>
                                <span className="text-sm text-zinc-400">{data.lab_reports.total_pending} pending</span>
                            </div>

                            <div className="space-y-2">
                                {data.lab_reports.urgent.map((report, i) => (
                                    <div
                                        key={i}
                                        className={`p-3 rounded-lg border ${getUrgencyColor(report.urgency)}`}
                                    >
                                        <div className="flex items-center justify-between">
                                            <div>
                                                <span
                                                    className="text-xs px-2 py-0.5 rounded mr-2"
                                                    style={{ backgroundColor: report.color, color: 'white' }}
                                                >
                                                    {report.subject_code}
                                                </span>
                                                <span className="font-medium text-white">{report.experiment_name}</span>
                                            </div>
                                            <div className="text-right">
                                                <p className="text-sm font-medium">
                                                    {report.days_remaining < 0 ? (
                                                        <span className="text-red-400">Overdue by {Math.abs(report.days_remaining)}d</span>
                                                    ) : report.days_remaining === 0 ? (
                                                        <span className="text-orange-400">Due Today</span>
                                                    ) : (
                                                        <span>{report.days_remaining} days left</span>
                                                    )}
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Upcoming Deadlines */}
                    {data.deadlines.length > 0 && (
                        <div className="glass rounded-2xl p-6">
                            <h2 className="text-lg font-semibold text-white mb-4">Upcoming Deadlines</h2>

                            <div className="space-y-2">
                                {data.deadlines.map((deadline, i) => (
                                    <div
                                        key={i}
                                        className="flex items-center justify-between p-3 rounded-lg bg-surface-light"
                                    >
                                        <div className="flex items-center gap-3">
                                            <span className="text-lg">
                                                {deadline.type === 'lab_report' ? '🧪' :
                                                 deadline.type === 'assignment' ? '📝' :
                                                 deadline.type === 'goal' ? '🎯' : '📅'}
                                            </span>
                                            <div>
                                                <p className="font-medium text-white">{deadline.title}</p>
                                                {deadline.subject_code && (
                                                    <span className="text-xs text-zinc-500">{deadline.subject_code}</span>
                                                )}
                                            </div>
                                        </div>
                                        <div className={`text-sm font-medium ${
                                            deadline.days_remaining <= 0 ? 'text-red-400' :
                                            deadline.days_remaining <= 2 ? 'text-orange-400' :
                                            deadline.days_remaining <= 7 ? 'text-yellow-400' : 'text-zinc-400'
                                        }`}>
                                            {deadline.days_remaining < 0 ? 'Overdue' :
                                             deadline.days_remaining === 0 ? 'Today' :
                                             deadline.days_remaining === 1 ? 'Tomorrow' :
                                             `${deadline.days_remaining} days`}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Tasks */}
                    {data.tasks.scheduled.length > 0 && (
                        <div className="glass rounded-2xl p-6">
                            <div className="flex items-center justify-between mb-4">
                                <h2 className="text-lg font-semibold text-white">Today's Tasks</h2>
                                <span className="text-sm text-zinc-400">
                                    {data.tasks.completed}/{data.tasks.count} done
                                </span>
                            </div>

                            <div className="space-y-2">
                                {data.tasks.scheduled.map((task) => (
                                    <div
                                        key={task.id}
                                        className={`flex items-center gap-3 p-3 rounded-lg ${
                                            task.status === 'completed' ? 'bg-green-500/10 opacity-60' : 'bg-surface-light'
                                        }`}
                                    >
                                        <div className={`w-4 h-4 rounded-full border-2 ${
                                            task.status === 'completed' ? 'bg-green-500 border-green-500' : 'border-zinc-500'
                                        }`}>
                                            {task.status === 'completed' && (
                                                <svg className="w-3 h-3 text-white m-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                                </svg>
                                            )}
                                        </div>
                                        <div className="flex-1">
                                            <p className={`font-medium ${task.status === 'completed' ? 'line-through text-zinc-500' : 'text-white'}`}>
                                                {task.title}
                                            </p>
                                            <div className="flex items-center gap-2 mt-1">
                                                {task.subject_code && (
                                                    <span
                                                        className="text-xs px-1.5 py-0.5 rounded"
                                                        style={{ backgroundColor: task.color || '#6366f1', color: 'white' }}
                                                    >
                                                        {task.subject_code}
                                                    </span>
                                                )}
                                                <span className="text-xs text-zinc-500">{task.duration_mins}min</span>
                                                {task.is_deep_work && (
                                                    <span className="text-xs text-green-400">Deep Work</span>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
