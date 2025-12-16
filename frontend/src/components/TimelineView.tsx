'use client'

import { useEffect, useState } from 'react'

interface TimelineBlock {
    type: string
    start: string
    end: string
    duration_mins: number
    label: string
    subject?: string
    room?: string
    task_id?: number
    is_deep_work?: boolean
    fixed: boolean
    energy_required: number
}

interface Gap {
    start: string
    end: string
    duration_mins: number
    is_deep_work_suitable: boolean
}

interface TimelineData {
    date: string
    day: string
    timeline: TimelineBlock[]
    gaps: Gap[]
    total_scheduled_mins: number
    deep_work_scheduled_mins: number
    config: {
        sleep_start: string
        sleep_end: string
        lunch_time: string
        dinner_time: string
    }
}

interface OptimizedSchedule {
    date: string
    day: string
    timetable: any[]
    optimized_schedule: {
        item_id?: number
        item_type: string
        title: string
        subject?: string
        start: string
        duration_mins: number
        priority?: number
        is_deep_work: boolean
    }[]
    items_scheduled: number
    total_study_mins: number
    deep_work_mins: number
    remaining_gaps: Gap[]
    unscheduled_items: number
}

export default function TimelineView() {
    const [timeline, setTimeline] = useState<TimelineData | null>(null)
    const [optimized, setOptimized] = useState<OptimizedSchedule | null>(null)
    const [loading, setLoading] = useState(true)
    const [view, setView] = useState<'timeline' | 'optimized'>('timeline')
    const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0])

    useEffect(() => {
        fetchData()
    }, [selectedDate])

    const fetchData = async () => {
        setLoading(true)
        try {
            const [timelineRes, optimizedRes] = await Promise.all([
                fetch(`/api/timeline/${selectedDate}`),
                fetch(`/api/timeline/optimize/${selectedDate}`, { method: 'POST' })
            ])

            if (timelineRes.ok) {
                const data = await timelineRes.json()
                setTimeline(data)
            }

            if (optimizedRes.ok) {
                const data = await optimizedRes.json()
                setOptimized(data)
            }
        } catch (error) {
            console.error('Failed to fetch timeline:', error)
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
        if (hours > 0) return `${hours}h ${minutes}m`
        return `${minutes}m`
    }

    const getActivityColor = (type: string) => {
        const colors: Record<string, { bg: string; text: string; border: string }> = {
            'sleep': { bg: 'bg-indigo-500/20', text: 'text-indigo-400', border: 'border-indigo-500/30' },
            'wake_routine': { bg: 'bg-cyan-500/20', text: 'text-cyan-400', border: 'border-cyan-500/30' },
            'breakfast': { bg: 'bg-amber-500/20', text: 'text-amber-400', border: 'border-amber-500/30' },
            'lunch': { bg: 'bg-orange-500/20', text: 'text-orange-400', border: 'border-orange-500/30' },
            'dinner': { bg: 'bg-orange-500/20', text: 'text-orange-400', border: 'border-orange-500/30' },
            'university': { bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500/30' },
            'study': { bg: 'bg-green-500/20', text: 'text-green-400', border: 'border-green-500/30' },
            'revision': { bg: 'bg-purple-500/20', text: 'text-purple-400', border: 'border-purple-500/30' },
            'practice': { bg: 'bg-pink-500/20', text: 'text-pink-400', border: 'border-pink-500/30' },
            'assignment': { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/30' },
            'lab_work': { bg: 'bg-teal-500/20', text: 'text-teal-400', border: 'border-teal-500/30' },
            'deep_work': { bg: 'bg-emerald-500/20', text: 'text-emerald-400', border: 'border-emerald-500/30' },
            'break': { bg: 'bg-zinc-500/20', text: 'text-zinc-400', border: 'border-zinc-500/30' },
            'free_time': { bg: 'bg-sky-500/20', text: 'text-sky-400', border: 'border-sky-500/30' },
        }
        return colors[type] || { bg: 'bg-zinc-500/10', text: 'text-zinc-400', border: 'border-zinc-500/20' }
    }

    const getActivityIcon = (type: string) => {
        const icons: Record<string, string> = {
            'sleep': '🌙',
            'wake_routine': '☀️',
            'breakfast': '🍳',
            'lunch': '🍽️',
            'dinner': '🍲',
            'university': '🎓',
            'study': '📖',
            'revision': '🔄',
            'practice': '✍️',
            'assignment': '📝',
            'lab_work': '🧪',
            'deep_work': '🎯',
            'break': '☕',
            'free_time': '🎮',
        }
        return icons[type] || '📌'
    }

    const applyOptimization = async () => {
        if (!optimized?.optimized_schedule) return

        for (const block of optimized.optimized_schedule) {
            if (block.item_type === 'break') continue

            try {
                const formData = new FormData()
                formData.append('date', selectedDate)
                formData.append('start_time', block.start)
                formData.append('duration_mins', block.duration_mins.toString())
                formData.append('activity_type', block.item_type)
                formData.append('title', block.title)
                if (block.subject) formData.append('subject_code', block.subject)
                formData.append('priority', (block.priority || 5).toString())

                await fetch('/api/timeline/blocks', {
                    method: 'POST',
                    body: formData
                })
            } catch (error) {
                console.error('Failed to create block:', error)
            }
        }

        fetchData()
    }

    const navigateDate = (delta: number) => {
        const current = new Date(selectedDate)
        current.setDate(current.getDate() + delta)
        setSelectedDate(current.toISOString().split('T')[0])
    }

    if (loading) {
        return (
            <div className="glass rounded-2xl p-6">
                <div className="animate-pulse space-y-4">
                    <div className="h-8 bg-zinc-700 rounded w-1/3"></div>
                    <div className="space-y-3">
                        {[1, 2, 3, 4, 5].map(i => (
                            <div key={i} className="h-16 bg-zinc-700 rounded-xl"></div>
                        ))}
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="glass rounded-2xl p-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h2 className="text-xl font-bold text-white flex items-center gap-2">
                        <span>📅</span> Day Timeline
                    </h2>
                    <p className="text-sm text-zinc-400 mt-1">
                        {timeline?.day}, {new Date(selectedDate).toLocaleDateString('en-US', { month: 'long', day: 'numeric' })}
                    </p>
                </div>

                <div className="flex items-center gap-2">
                    {/* Date Navigation */}
                    <button
                        onClick={() => navigateDate(-1)}
                        className="p-2 rounded-lg bg-surface-light hover:bg-surface text-zinc-400 hover:text-white"
                    >
                        ←
                    </button>
                    <input
                        type="date"
                        value={selectedDate}
                        onChange={(e) => setSelectedDate(e.target.value)}
                        className="px-3 py-2 rounded-lg bg-surface border border-white/10 text-white"
                    />
                    <button
                        onClick={() => navigateDate(1)}
                        className="p-2 rounded-lg bg-surface-light hover:bg-surface text-zinc-400 hover:text-white"
                    >
                        →
                    </button>
                </div>
            </div>

            {/* View Toggle */}
            <div className="flex gap-2 mb-6">
                <button
                    onClick={() => setView('timeline')}
                    className={`px-4 py-2 rounded-lg transition-colors ${
                        view === 'timeline'
                            ? 'bg-primary text-white'
                            : 'bg-surface-light text-zinc-400 hover:text-white'
                    }`}
                >
                    Full Timeline
                </button>
                <button
                    onClick={() => setView('optimized')}
                    className={`px-4 py-2 rounded-lg transition-colors ${
                        view === 'optimized'
                            ? 'bg-primary text-white'
                            : 'bg-surface-light text-zinc-400 hover:text-white'
                    }`}
                >
                    Optimized Schedule
                </button>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="p-3 rounded-lg bg-surface-light">
                    <p className="text-2xl font-bold text-white">
                        {formatDuration(view === 'timeline' ? timeline?.total_scheduled_mins || 0 : optimized?.total_study_mins || 0)}
                    </p>
                    <p className="text-xs text-zinc-400">Scheduled</p>
                </div>
                <div className="p-3 rounded-lg bg-green-500/10">
                    <p className="text-2xl font-bold text-green-400">
                        {formatDuration(view === 'timeline' ? timeline?.deep_work_scheduled_mins || 0 : optimized?.deep_work_mins || 0)}
                    </p>
                    <p className="text-xs text-zinc-400">Deep Work</p>
                </div>
                {view === 'optimized' && (
                    <div className="p-3 rounded-lg bg-yellow-500/10">
                        <p className="text-2xl font-bold text-yellow-400">{optimized?.unscheduled_items || 0}</p>
                        <p className="text-xs text-zinc-400">Remaining</p>
                    </div>
                )}
            </div>

            {/* Timeline/Schedule View */}
            {view === 'timeline' && timeline && (
                <div className="space-y-2">
                    {timeline.timeline.map((block, idx) => {
                        const colors = getActivityColor(block.type)
                        const icon = getActivityIcon(block.type)

                        return (
                            <div
                                key={idx}
                                className={`flex items-center gap-4 p-3 rounded-xl border ${colors.bg} ${colors.border}`}
                            >
                                <div className="text-2xl">{icon}</div>
                                <div className="flex-1">
                                    <div className="flex items-center gap-2">
                                        <span className={`font-medium ${colors.text}`}>{block.label}</span>
                                        {block.is_deep_work && (
                                            <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400">
                                                Deep Work
                                            </span>
                                        )}
                                        {block.fixed && (
                                            <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-500/20 text-zinc-400">
                                                Fixed
                                            </span>
                                        )}
                                    </div>
                                    {block.subject && (
                                        <span className="text-xs text-zinc-500">{block.subject}</span>
                                    )}
                                    {block.room && (
                                        <span className="text-xs text-zinc-500 ml-2">📍 {block.room}</span>
                                    )}
                                </div>
                                <div className="text-right">
                                    <p className="text-sm text-zinc-400">
                                        {formatTime(block.start)} - {formatTime(block.end)}
                                    </p>
                                    <p className={`text-sm font-medium ${colors.text}`}>
                                        {formatDuration(block.duration_mins)}
                                    </p>
                                </div>
                            </div>
                        )
                    })}

                    {/* Gaps */}
                    {timeline.gaps.length > 0 && (
                        <div className="mt-4 pt-4 border-t border-white/10">
                            <h3 className="text-sm font-medium text-zinc-400 mb-3">Available Gaps</h3>
                            {timeline.gaps.map((gap, idx) => (
                                <div
                                    key={idx}
                                    className={`flex items-center justify-between p-3 rounded-lg mb-2 ${
                                        gap.is_deep_work_suitable
                                            ? 'bg-green-500/10 border border-green-500/20'
                                            : 'bg-surface-light'
                                    }`}
                                >
                                    <div className="flex items-center gap-2">
                                        <span className="text-sm text-zinc-400">
                                            {formatTime(gap.start)} - {formatTime(gap.end)}
                                        </span>
                                        {gap.is_deep_work_suitable && (
                                            <span className="text-xs text-green-400">Deep Work OK</span>
                                        )}
                                    </div>
                                    <span className="font-medium text-white">
                                        {formatDuration(gap.duration_mins)}
                                    </span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {view === 'optimized' && optimized && (
                <div className="space-y-2">
                    {optimized.optimized_schedule.length === 0 ? (
                        <div className="text-center py-8">
                            <p className="text-zinc-400">No items to schedule</p>
                        </div>
                    ) : (
                        <>
                            {optimized.optimized_schedule.map((block, idx) => {
                                const colors = getActivityColor(block.item_type)
                                const icon = getActivityIcon(block.item_type)

                                return (
                                    <div
                                        key={idx}
                                        className={`flex items-center gap-4 p-3 rounded-xl border ${colors.bg} ${colors.border}`}
                                    >
                                        <div className="text-2xl">{icon}</div>
                                        <div className="flex-1">
                                            <div className="flex items-center gap-2">
                                                <span className={`font-medium ${colors.text}`}>{block.title}</span>
                                                {block.is_deep_work && (
                                                    <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400">
                                                        Deep
                                                    </span>
                                                )}
                                            </div>
                                            <div className="flex items-center gap-2 mt-1">
                                                {block.subject && (
                                                    <span className="text-xs px-2 py-0.5 rounded bg-primary/20 text-primary">
                                                        {block.subject}
                                                    </span>
                                                )}
                                                <span className="text-xs text-zinc-500 capitalize">
                                                    {block.item_type.replace('_', ' ')}
                                                </span>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <p className="text-sm text-zinc-400">{formatTime(block.start)}</p>
                                            <p className={`text-sm font-medium ${colors.text}`}>
                                                {formatDuration(block.duration_mins)}
                                            </p>
                                        </div>
                                    </div>
                                )
                            })}

                            {/* Apply Button */}
                            <button
                                onClick={applyOptimization}
                                className="w-full mt-4 py-3 rounded-lg bg-primary text-white font-medium hover:bg-primary/90 transition-colors"
                            >
                                Apply Optimized Schedule
                            </button>
                        </>
                    )}

                    {/* Remaining Gaps */}
                    {optimized.remaining_gaps.length > 0 && (
                        <div className="mt-4 pt-4 border-t border-white/10">
                            <h3 className="text-sm font-medium text-zinc-400 mb-3">Still Available</h3>
                            {optimized.remaining_gaps.map((gap, idx) => (
                                <div
                                    key={idx}
                                    className="flex items-center justify-between p-3 rounded-lg bg-surface-light mb-2"
                                >
                                    <span className="text-sm text-zinc-400">
                                        {formatTime(gap.start)} ({formatDuration(gap.duration_mins)})
                                    </span>
                                    {gap.is_deep_work_suitable && (
                                        <span className="text-xs text-green-400">Deep Work</span>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}
