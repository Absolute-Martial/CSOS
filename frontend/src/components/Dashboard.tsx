'use client'

import { useEffect, useState } from 'react'

interface Task {
    id: number
    title: string
    subject_code: string
    color: string
    scheduled_start: string
    scheduled_end: string
    duration_mins: number
    priority: number
    status: string
    is_deep_work: boolean
}

interface Revision {
    revision_id: number
    chapter_number: number
    chapter_title: string
    subject_code: string
    subject_credits: number
    color: string
    due_date: string
}

interface Subject {
    id: number
    code: string
    name: string
    credits: number
    color: string
}

export default function Dashboard() {
    const [tasks, setTasks] = useState<Task[]>([])
    const [revisions, setRevisions] = useState<Revision[]>([])
    const [subjects, setSubjects] = useState<Subject[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        Promise.all([
            fetch('/api/tasks/today').then(r => r.json()).catch(() => []),
            fetch('/api/revisions/pending').then(r => r.json()).catch(() => []),
            fetch('/api/subjects').then(r => r.json()).catch(() => [])
        ]).then(([tasksData, revisionsData, subjectsData]) => {
            setTasks(tasksData || [])
            setRevisions(revisionsData || [])
            setSubjects(subjectsData || [])
            setLoading(false)
        })
    }, [])

    const formatTime = (dateString: string) => {
        if (!dateString) return '--:--'
        const date = new Date(dateString)
        return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
    }

    const getTimelinePosition = (timeString: string) => {
        if (!timeString) return 0
        const date = new Date(timeString)
        const hours = date.getHours()
        const minutes = date.getMinutes()
        // Day goes from 04:30 to 22:30 = 18 hours
        const totalMins = (hours - 4) * 60 + (minutes - 30)
        return Math.max(0, Math.min(100, (totalMins / (18 * 60)) * 100))
    }

    if (loading) {
        return (
            <div className="glass rounded-2xl p-6 animate-pulse">
                <div className="h-8 bg-surface-light rounded w-1/3 mb-4"></div>
                <div className="space-y-3">
                    {[1, 2, 3].map(i => (
                        <div key={i} className="h-20 bg-surface-light rounded-xl"></div>
                    ))}
                </div>
            </div>
        )
    }

    return (
        <div className="space-y-6">
            {/* Subject Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {subjects.map(subject => (
                    <div
                        key={subject.id}
                        className="glass rounded-xl p-4 card-hover cursor-pointer"
                        style={{ borderLeft: `4px solid ${subject.color}` }}
                    >
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-2xl font-bold" style={{ color: subject.color }}>
                                {subject.code}
                            </span>
                            <span className="text-xs px-2 py-1 rounded-full bg-white/10">
                                {subject.credits} cr
                            </span>
                        </div>
                        <p className="text-sm text-zinc-400 truncate">{subject.name}</p>
                    </div>
                ))}
            </div>

            {/* Today's Schedule */}
            <div className="glass rounded-2xl p-6">
                <div className="flex items-center justify-between mb-6">
                    <h3 className="text-lg font-semibold text-white">Today's Schedule</h3>
                    <div className="flex items-center gap-2 text-sm text-zinc-400">
                        <span className="w-3 h-3 rounded-full bg-primary"></span>
                        04:30 - 22:30
                    </div>
                </div>

                {/* Timeline */}
                <div className="relative">
                    {/* Time markers */}
                    <div className="flex justify-between text-xs text-zinc-500 mb-2">
                        <span>04:30</span>
                        <span>08:00</span>
                        <span>12:00</span>
                        <span>16:00</span>
                        <span>20:00</span>
                        <span>22:30</span>
                    </div>

                    {/* Timeline bar */}
                    <div className="h-2 bg-surface-light rounded-full relative overflow-hidden">
                        {/* Current time indicator */}
                        <div
                            className="absolute top-0 w-1 h-full bg-white shadow-lg z-10"
                            style={{ left: `${getTimelinePosition(new Date().toISOString())}%` }}
                        />

                        {/* Task blocks */}
                        {tasks.map(task => (
                            <div
                                key={task.id}
                                className="absolute top-0 h-full rounded-full"
                                style={{
                                    left: `${getTimelinePosition(task.scheduled_start)}%`,
                                    width: `${(task.duration_mins / (18 * 60)) * 100}%`,
                                    backgroundColor: task.color || '#6366f1',
                                    opacity: task.status === 'completed' ? 0.5 : 1
                                }}
                            />
                        ))}
                    </div>
                </div>

                {/* Task List */}
                <div className="mt-6 space-y-3">
                    {tasks.length === 0 ? (
                        <p className="text-center text-zinc-500 py-8">No tasks scheduled for today</p>
                    ) : (
                        tasks.map(task => (
                            <div
                                key={task.id}
                                className="flex items-center gap-4 p-4 rounded-xl bg-surface-light/50 hover:bg-surface-light transition"
                            >
                                <div
                                    className="w-1 h-12 rounded-full"
                                    style={{ backgroundColor: task.color || '#6366f1' }}
                                />
                                <div className="flex-1">
                                    <div className="flex items-center gap-2">
                                        <h4 className="font-medium text-white">{task.title}</h4>
                                        {task.is_deep_work && (
                                            <span className="text-xs px-2 py-0.5 rounded-full bg-primary/20 text-primary">
                                                Deep Work
                                            </span>
                                        )}
                                    </div>
                                    <p className="text-sm text-zinc-400">
                                        {task.subject_code} • {formatTime(task.scheduled_start)} - {formatTime(task.scheduled_end)}
                                    </p>
                                </div>
                                <div className="text-right">
                                    <p className="text-lg font-semibold text-white">{task.duration_mins}m</p>
                                    <p className="text-xs text-zinc-500">P{task.priority}</p>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* Pending Revisions */}
            <div className="glass rounded-2xl p-6">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-white">📚 Revision Queue</h3>
                    <span className="text-sm text-zinc-400">{revisions.length} pending</span>
                </div>

                {revisions.length === 0 ? (
                    <p className="text-center text-zinc-500 py-4">No revisions due. Great job! 🎉</p>
                ) : (
                    <div className="space-y-2">
                        {revisions.slice(0, 5).map((rev, index) => (
                            <div
                                key={rev.revision_id}
                                className="flex items-center gap-3 p-3 rounded-lg bg-surface-light/50 hover:bg-surface-light transition cursor-pointer"
                            >
                                <div
                                    className="w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold"
                                    style={{ backgroundColor: rev.color || '#6366f1' }}
                                >
                                    {index + 1}
                                </div>
                                <div className="flex-1">
                                    <p className="font-medium text-white">
                                        {rev.subject_code} Ch.{rev.chapter_number}
                                    </p>
                                    <p className="text-xs text-zinc-400">{rev.chapter_title}</p>
                                </div>
                                <div className="text-right">
                                    <span className={`text-sm font-medium ${new Date(rev.due_date) <= new Date() ? 'text-red-400' : 'text-zinc-400'
                                        }`}>
                                        {new Date(rev.due_date) <= new Date() ? '⏰ Due' : rev.due_date}
                                    </span>
                                    <p className="text-xs text-zinc-500">{rev.subject_credits} credits</p>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}
