'use client'

import { useEffect, useState } from 'react'

interface Goal {
    id: number
    title: string
    description?: string
    category_id?: number
    subject_id?: number
    target_value?: number
    current_value: number
    unit?: string
    deadline?: string
    priority: number
    completed: boolean
    completed_at?: string
    category_name?: string
    category_color?: string
    category_icon?: string
    subject_code?: string
    subject_name?: string
    subject_color?: string
    progress_percent: number
    days_remaining?: number
}

interface Category {
    id: number
    name: string
    color: string
    icon: string
    goal_count: number
    completed_count: number
}

interface GoalsSummary {
    totals: {
        total: number
        completed: number
        active: number
        overdue: number
        due_this_week: number
        completion_rate: number
    }
    by_category: Category[]
}

export default function GoalTracker() {
    const [goals, setGoals] = useState<Goal[]>([])
    const [summary, setSummary] = useState<GoalsSummary | null>(null)
    const [loading, setLoading] = useState(true)
    const [showCreateModal, setShowCreateModal] = useState(false)
    const [showCompleted, setShowCompleted] = useState(false)

    // Form state
    const [newGoal, setNewGoal] = useState({
        title: '',
        description: '',
        target_value: '',
        unit: '',
        deadline: '',
        priority: 5
    })
    const [creating, setCreating] = useState(false)

    useEffect(() => {
        fetchGoals()
        fetchSummary()
    }, [showCompleted])

    const fetchGoals = async () => {
        try {
            const url = showCompleted
                ? '/api/goals?include_completed=true'
                : '/api/goals'
            const res = await fetch(url)
            if (res.ok) {
                const data = await res.json()
                setGoals(data)
            }
        } catch (error) {
            console.error('Failed to fetch goals:', error)
        } finally {
            setLoading(false)
        }
    }

    const fetchSummary = async () => {
        try {
            const res = await fetch('/api/goals/summary/stats')
            if (res.ok) {
                const data = await res.json()
                setSummary(data)
            }
        } catch (error) {
            console.error('Failed to fetch summary:', error)
        }
    }

    const createGoal = async () => {
        if (!newGoal.title.trim()) return
        setCreating(true)

        try {
            const res = await fetch('/api/goals', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: newGoal.title,
                    description: newGoal.description || null,
                    target_value: newGoal.target_value ? parseInt(newGoal.target_value) : null,
                    unit: newGoal.unit || null,
                    deadline: newGoal.deadline || null,
                    priority: newGoal.priority
                })
            })

            if (res.ok) {
                await fetchGoals()
                await fetchSummary()
                setShowCreateModal(false)
                setNewGoal({
                    title: '',
                    description: '',
                    target_value: '',
                    unit: '',
                    deadline: '',
                    priority: 5
                })
            }
        } catch (error) {
            console.error('Failed to create goal:', error)
        } finally {
            setCreating(false)
        }
    }

    const updateProgress = async (goalId: number, delta: number) => {
        try {
            const res = await fetch(`/api/goals/${goalId}/progress`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ progress_delta: delta })
            })

            if (res.ok) {
                await fetchGoals()
                await fetchSummary()
            }
        } catch (error) {
            console.error('Failed to update progress:', error)
        }
    }

    const toggleComplete = async (goalId: number, currentCompleted: boolean) => {
        try {
            const res = await fetch(`/api/goals/${goalId}/progress`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mark_complete: !currentCompleted })
            })

            if (res.ok) {
                await fetchGoals()
                await fetchSummary()
            }
        } catch (error) {
            console.error('Failed to toggle completion:', error)
        }
    }

    const getPriorityColor = (priority: number) => {
        if (priority <= 3) return 'text-red-400'
        if (priority <= 5) return 'text-yellow-400'
        return 'text-green-400'
    }

    const getDeadlineStatus = (daysRemaining?: number) => {
        if (daysRemaining === undefined || daysRemaining === null) return null
        if (daysRemaining < 0) return { text: 'Overdue', color: 'text-red-400 bg-red-500/20' }
        if (daysRemaining === 0) return { text: 'Due today', color: 'text-orange-400 bg-orange-500/20' }
        if (daysRemaining <= 3) return { text: `${daysRemaining}d left`, color: 'text-yellow-400 bg-yellow-500/20' }
        return { text: `${daysRemaining}d left`, color: 'text-zinc-400 bg-zinc-500/20' }
    }

    if (loading) {
        return (
            <div className="glass rounded-2xl p-6">
                <div className="animate-pulse space-y-4">
                    <div className="h-6 bg-zinc-700 rounded w-1/3"></div>
                    <div className="space-y-2">
                        {[1, 2, 3].map(i => (
                            <div key={i} className="h-16 bg-zinc-700 rounded-xl"></div>
                        ))}
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="space-y-6">
            {/* Summary Cards */}
            {summary && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="glass rounded-xl p-4">
                        <p className="text-3xl font-bold text-white">{summary.totals.active}</p>
                        <p className="text-sm text-zinc-400">Active Goals</p>
                    </div>
                    <div className="glass rounded-xl p-4">
                        <p className="text-3xl font-bold text-green-400">{summary.totals.completed}</p>
                        <p className="text-sm text-zinc-400">Completed</p>
                    </div>
                    <div className="glass rounded-xl p-4">
                        <p className="text-3xl font-bold text-primary">{summary.totals.completion_rate}%</p>
                        <p className="text-sm text-zinc-400">Success Rate</p>
                    </div>
                    <div className="glass rounded-xl p-4">
                        <p className={`text-3xl font-bold ${summary.totals.overdue > 0 ? 'text-red-400' : 'text-zinc-400'}`}>
                            {summary.totals.overdue}
                        </p>
                        <p className="text-sm text-zinc-400">Overdue</p>
                    </div>
                </div>
            )}

            {/* Goals List */}
            <div className="glass rounded-2xl p-6">
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <h2 className="text-xl font-bold text-white">Study Goals</h2>
                        {summary && summary.totals.due_this_week > 0 && (
                            <p className="text-sm text-yellow-400 mt-1">
                                {summary.totals.due_this_week} due this week
                            </p>
                        )}
                    </div>
                    <div className="flex items-center gap-3">
                        <label className="flex items-center gap-2 text-sm text-zinc-400">
                            <input
                                type="checkbox"
                                checked={showCompleted}
                                onChange={(e) => setShowCompleted(e.target.checked)}
                                className="rounded border-white/20 bg-surface"
                            />
                            Show completed
                        </label>
                        <button
                            onClick={() => setShowCreateModal(true)}
                            className="px-4 py-2 rounded-lg bg-primary/20 hover:bg-primary/30 text-primary transition-colors"
                        >
                            + New Goal
                        </button>
                    </div>
                </div>

                {goals.length === 0 ? (
                    <div className="text-center py-8">
                        <p className="text-zinc-400 mb-4">No goals yet</p>
                        <button
                            onClick={() => setShowCreateModal(true)}
                            className="text-primary hover:underline"
                        >
                            Create your first goal
                        </button>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {goals.map(goal => {
                            const deadlineStatus = getDeadlineStatus(goal.days_remaining)

                            return (
                                <div
                                    key={goal.id}
                                    className={`p-4 rounded-xl bg-surface-light transition-colors ${
                                        goal.completed ? 'opacity-60' : ''
                                    }`}
                                >
                                    <div className="flex items-start gap-3">
                                        {/* Checkbox */}
                                        <button
                                            onClick={() => toggleComplete(goal.id, goal.completed)}
                                            className={`mt-1 w-5 h-5 rounded-full border-2 flex items-center justify-center transition-colors ${
                                                goal.completed
                                                    ? 'bg-green-500 border-green-500'
                                                    : 'border-zinc-500 hover:border-green-500'
                                            }`}
                                        >
                                            {goal.completed && (
                                                <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                                </svg>
                                            )}
                                        </button>

                                        {/* Content */}
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 flex-wrap">
                                                {goal.category_icon && (
                                                    <span>{goal.category_icon}</span>
                                                )}
                                                <h3 className={`font-medium ${goal.completed ? 'text-zinc-400 line-through' : 'text-white'}`}>
                                                    {goal.title}
                                                </h3>
                                                {goal.subject_code && (
                                                    <span
                                                        className="text-xs px-2 py-0.5 rounded"
                                                        style={{
                                                            backgroundColor: goal.subject_color || '#6366f1',
                                                            color: 'white'
                                                        }}
                                                    >
                                                        {goal.subject_code}
                                                    </span>
                                                )}
                                                {deadlineStatus && (
                                                    <span className={`text-xs px-2 py-0.5 rounded ${deadlineStatus.color}`}>
                                                        {deadlineStatus.text}
                                                    </span>
                                                )}
                                            </div>

                                            {goal.description && (
                                                <p className="text-sm text-zinc-400 mt-1 line-clamp-1">
                                                    {goal.description}
                                                </p>
                                            )}

                                            {/* Progress bar for measurable goals */}
                                            {goal.target_value && !goal.completed && (
                                                <div className="mt-3">
                                                    <div className="flex items-center justify-between text-sm mb-1">
                                                        <span className="text-zinc-400">
                                                            {goal.current_value} / {goal.target_value} {goal.unit}
                                                        </span>
                                                        <span className="text-primary">{goal.progress_percent}%</span>
                                                    </div>
                                                    <div className="h-2 bg-surface rounded-full overflow-hidden">
                                                        <div
                                                            className="h-full bg-primary rounded-full transition-all"
                                                            style={{ width: `${Math.min(goal.progress_percent, 100)}%` }}
                                                        />
                                                    </div>
                                                    <div className="flex gap-2 mt-2">
                                                        <button
                                                            onClick={() => updateProgress(goal.id, 1)}
                                                            className="px-2 py-1 text-xs rounded bg-primary/20 text-primary hover:bg-primary/30"
                                                        >
                                                            +1
                                                        </button>
                                                        <button
                                                            onClick={() => updateProgress(goal.id, 5)}
                                                            className="px-2 py-1 text-xs rounded bg-primary/20 text-primary hover:bg-primary/30"
                                                        >
                                                            +5
                                                        </button>
                                                        <button
                                                            onClick={() => updateProgress(goal.id, -1)}
                                                            className="px-2 py-1 text-xs rounded bg-red-500/20 text-red-400 hover:bg-red-500/30"
                                                        >
                                                            -1
                                                        </button>
                                                    </div>
                                                </div>
                                            )}
                                        </div>

                                        {/* Priority indicator */}
                                        <div className={`text-sm ${getPriorityColor(goal.priority)}`}>
                                            P{goal.priority}
                                        </div>
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                )}
            </div>

            {/* Create Modal */}
            {showCreateModal && (
                <>
                    <div
                        className="fixed inset-0 bg-black/50 z-50"
                        onClick={() => setShowCreateModal(false)}
                    />
                    <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md glass rounded-2xl p-6 z-50 max-h-[90vh] overflow-y-auto">
                        <h3 className="text-lg font-bold text-white mb-4">Create New Goal</h3>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm text-zinc-400 mb-1">Goal Title *</label>
                                <input
                                    type="text"
                                    value={newGoal.title}
                                    onChange={(e) => setNewGoal({ ...newGoal, title: e.target.value })}
                                    placeholder="e.g., Complete Data Structures assignments"
                                    className="w-full px-4 py-2 rounded-lg bg-surface border border-white/10 text-white placeholder-zinc-500 focus:outline-none focus:border-primary"
                                />
                            </div>

                            <div>
                                <label className="block text-sm text-zinc-400 mb-1">Description</label>
                                <textarea
                                    value={newGoal.description}
                                    onChange={(e) => setNewGoal({ ...newGoal, description: e.target.value })}
                                    placeholder="Add more details..."
                                    rows={2}
                                    className="w-full px-4 py-2 rounded-lg bg-surface border border-white/10 text-white placeholder-zinc-500 focus:outline-none focus:border-primary resize-none"
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm text-zinc-400 mb-1">Target Value</label>
                                    <input
                                        type="number"
                                        value={newGoal.target_value}
                                        onChange={(e) => setNewGoal({ ...newGoal, target_value: e.target.value })}
                                        placeholder="e.g., 10"
                                        className="w-full px-4 py-2 rounded-lg bg-surface border border-white/10 text-white placeholder-zinc-500 focus:outline-none focus:border-primary"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm text-zinc-400 mb-1">Unit</label>
                                    <input
                                        type="text"
                                        value={newGoal.unit}
                                        onChange={(e) => setNewGoal({ ...newGoal, unit: e.target.value })}
                                        placeholder="e.g., chapters"
                                        className="w-full px-4 py-2 rounded-lg bg-surface border border-white/10 text-white placeholder-zinc-500 focus:outline-none focus:border-primary"
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm text-zinc-400 mb-1">Deadline</label>
                                    <input
                                        type="date"
                                        value={newGoal.deadline}
                                        onChange={(e) => setNewGoal({ ...newGoal, deadline: e.target.value })}
                                        className="w-full px-4 py-2 rounded-lg bg-surface border border-white/10 text-white focus:outline-none focus:border-primary"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm text-zinc-400 mb-1">Priority (1-10)</label>
                                    <input
                                        type="number"
                                        min="1"
                                        max="10"
                                        value={newGoal.priority}
                                        onChange={(e) => setNewGoal({ ...newGoal, priority: parseInt(e.target.value) || 5 })}
                                        className="w-full px-4 py-2 rounded-lg bg-surface border border-white/10 text-white focus:outline-none focus:border-primary"
                                    />
                                </div>
                            </div>
                        </div>

                        <div className="flex gap-3 mt-6">
                            <button
                                onClick={() => setShowCreateModal(false)}
                                className="flex-1 py-2 rounded-lg bg-surface-light text-zinc-400 hover:text-white transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={createGoal}
                                disabled={!newGoal.title.trim() || creating}
                                className="flex-1 py-2 rounded-lg bg-primary text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {creating ? 'Creating...' : 'Create Goal'}
                            </button>
                        </div>
                    </div>
                </>
            )}
        </div>
    )
}
