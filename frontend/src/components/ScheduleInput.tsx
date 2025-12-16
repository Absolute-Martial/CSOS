'use client'

import { useState } from 'react'

interface Props {
    onScheduleChange?: () => void
}

interface RedistributionPlan {
    success: boolean
    event: {
        type: string
        subject: string
        date: string
        days_until: number
    }
    study_needed_mins: number
    study_allocated_mins: number
    fully_scheduled: boolean
    blocks: {
        date: string
        day: string
        start: string
        duration_mins: number
        subject: string
        title: string
        is_deep_work: boolean
    }[]
    message: string
    applied?: boolean
    tasks_created?: number
}

export default function ScheduleInput({ onScheduleChange }: Props) {
    const [input, setInput] = useState('')
    const [loading, setLoading] = useState(false)
    const [plan, setPlan] = useState<RedistributionPlan | null>(null)
    const [error, setError] = useState<string | null>(null)

    const eventTypes = ['test', 'quiz', 'assignment', 'lab_report', 'project', 'exam']

    const parseInput = (text: string): { type: string; subject: string; date: string } | null => {
        // Simple parsing - in production, the AI would do this
        const lowerText = text.toLowerCase()

        // Find event type
        let eventType = 'test'
        for (const type of eventTypes) {
            if (lowerText.includes(type.replace('_', ' '))) {
                eventType = type
                break
            }
        }

        // Find subject code (4 letters + 3 numbers)
        const subjectMatch = text.match(/[A-Z]{4}[0-9]{3}/i)
        const subject = subjectMatch ? subjectMatch[0].toUpperCase() : ''

        // Find date keywords
        const today = new Date()
        let targetDate = new Date()

        if (lowerText.includes('tomorrow')) {
            targetDate.setDate(today.getDate() + 1)
        } else if (lowerText.includes('friday')) {
            const dayDiff = (5 - today.getDay() + 7) % 7 || 7
            targetDate.setDate(today.getDate() + dayDiff)
        } else if (lowerText.includes('monday')) {
            const dayDiff = (1 - today.getDay() + 7) % 7 || 7
            targetDate.setDate(today.getDate() + dayDiff)
        } else if (lowerText.includes('next week')) {
            targetDate.setDate(today.getDate() + 7)
        } else {
            // Try to find a date pattern
            const dateMatch = text.match(/(\d{4})-(\d{2})-(\d{2})/)
            if (dateMatch) {
                targetDate = new Date(dateMatch[0])
            }
        }

        if (!subject) {
            return null
        }

        return {
            type: eventType,
            subject,
            date: targetDate.toISOString().split('T')[0]
        }
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!input.trim()) return

        setLoading(true)
        setError(null)
        setPlan(null)

        const parsed = parseInput(input)
        if (!parsed) {
            setError('Could not understand the input. Please include a subject code (e.g., CHEM103)')
            setLoading(false)
            return
        }

        try {
            const formData = new FormData()
            formData.append('event_type', parsed.type)
            formData.append('subject_code', parsed.subject)
            formData.append('event_date', parsed.date)

            const res = await fetch('/api/schedule/redistribute', {
                method: 'POST',
                body: formData
            })

            if (res.ok) {
                const data = await res.json()
                setPlan(data)
            } else {
                const err = await res.json()
                setError(err.detail || 'Failed to create schedule plan')
            }
        } catch (err) {
            setError('Failed to connect to server')
        } finally {
            setLoading(false)
        }
    }

    const applyPlan = async () => {
        if (!plan) return

        setLoading(true)
        try {
            const formData = new FormData()
            formData.append('event_type', plan.event.type)
            formData.append('subject_code', plan.event.subject)
            formData.append('event_date', plan.event.date)
            formData.append('apply_immediately', 'true')

            const res = await fetch('/api/schedule/redistribute', {
                method: 'POST',
                body: formData
            })

            if (res.ok) {
                const data = await res.json()
                setPlan(data)
                onScheduleChange?.()
            }
        } catch (err) {
            setError('Failed to apply plan')
        } finally {
            setLoading(false)
        }
    }

    const formatDuration = (mins: number) => {
        const hours = Math.floor(mins / 60)
        const minutes = mins % 60
        if (hours > 0) return `${hours}h ${minutes}m`
        return `${minutes}m`
    }

    return (
        <div className="glass rounded-2xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Schedule Assistant</h2>
            <p className="text-sm text-zinc-400 mb-4">
                Tell me about upcoming events and I'll optimize your study schedule.
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="I have a surprise CHEM103 test on Friday"
                        className="w-full px-4 py-3 rounded-lg bg-surface border border-white/10 text-white placeholder-zinc-500 focus:outline-none focus:border-primary"
                        disabled={loading}
                    />
                </div>

                <button
                    type="submit"
                    disabled={loading || !input.trim()}
                    className="w-full py-3 rounded-lg bg-primary text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-primary/90 transition-colors"
                >
                    {loading ? 'Analyzing...' : 'Optimize Schedule'}
                </button>
            </form>

            {/* Example Commands */}
            <div className="mt-4 pt-4 border-t border-white/10">
                <p className="text-xs text-zinc-500 mb-2">Examples:</p>
                <div className="flex flex-wrap gap-2">
                    {[
                        'CHEM103 test on Friday',
                        'PHYS102 lab report tomorrow',
                        'MATH101 quiz next week'
                    ].map((example, i) => (
                        <button
                            key={i}
                            onClick={() => setInput(example)}
                            className="text-xs px-2 py-1 rounded bg-surface-light text-zinc-400 hover:text-white transition-colors"
                        >
                            {example}
                        </button>
                    ))}
                </div>
            </div>

            {/* Error Message */}
            {error && (
                <div className="mt-4 p-3 rounded-lg bg-red-500/20 border border-red-500/30 text-red-400 text-sm">
                    {error}
                </div>
            )}

            {/* Redistribution Plan */}
            {plan && plan.success && (
                <div className="mt-6 space-y-4">
                    <div className="flex items-center justify-between">
                        <h3 className="font-semibold text-white">Schedule Plan</h3>
                        {plan.applied && (
                            <span className="text-xs px-2 py-1 rounded-full bg-green-500/20 text-green-400">
                                Applied
                            </span>
                        )}
                    </div>

                    {/* Event Summary */}
                    <div className="p-4 rounded-lg bg-primary/20 border border-primary/30">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="font-medium text-white">
                                    {plan.event.subject} {plan.event.type.replace('_', ' ')}
                                </p>
                                <p className="text-sm text-zinc-400">
                                    {new Date(plan.event.date).toLocaleDateString('en-US', {
                                        weekday: 'long',
                                        month: 'short',
                                        day: 'numeric'
                                    })}
                                </p>
                            </div>
                            <div className="text-right">
                                <p className="text-2xl font-bold text-primary">{plan.event.days_until}</p>
                                <p className="text-xs text-zinc-400">days until</p>
                            </div>
                        </div>
                    </div>

                    {/* Study Allocation */}
                    <div className="grid grid-cols-2 gap-4">
                        <div className="p-3 rounded-lg bg-surface-light">
                            <p className="text-lg font-bold text-white">{formatDuration(plan.study_needed_mins)}</p>
                            <p className="text-xs text-zinc-400">Study needed</p>
                        </div>
                        <div className="p-3 rounded-lg bg-surface-light">
                            <p className={`text-lg font-bold ${plan.fully_scheduled ? 'text-green-400' : 'text-yellow-400'}`}>
                                {formatDuration(plan.study_allocated_mins)}
                            </p>
                            <p className="text-xs text-zinc-400">Allocated</p>
                        </div>
                    </div>

                    {/* Study Blocks */}
                    <div className="space-y-2">
                        <p className="text-sm font-medium text-zinc-400">Scheduled Study Blocks:</p>
                        {plan.blocks.map((block, i) => (
                            <div
                                key={i}
                                className={`flex items-center justify-between p-3 rounded-lg ${
                                    block.is_deep_work ? 'bg-green-500/10 border border-green-500/20' : 'bg-surface-light'
                                }`}
                            >
                                <div>
                                    <p className="font-medium text-white">{block.day}</p>
                                    <p className="text-sm text-zinc-400">{block.start}</p>
                                </div>
                                <div className="text-right">
                                    <p className="font-medium text-white">{formatDuration(block.duration_mins)}</p>
                                    {block.is_deep_work && (
                                        <p className="text-xs text-green-400">Deep Work</p>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Apply Button */}
                    {!plan.applied && (
                        <button
                            onClick={applyPlan}
                            disabled={loading}
                            className="w-full py-3 rounded-lg bg-green-500 text-white font-medium hover:bg-green-600 transition-colors disabled:opacity-50"
                        >
                            {loading ? 'Applying...' : 'Apply This Schedule'}
                        </button>
                    )}

                    {plan.applied && plan.tasks_created && (
                        <div className="p-3 rounded-lg bg-green-500/20 text-center">
                            <p className="text-green-400">
                                Created {plan.tasks_created} study tasks in your schedule
                            </p>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}
