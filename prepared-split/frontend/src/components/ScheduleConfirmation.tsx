'use client'

import { useCopilotContext, ScheduleChange } from '@/providers/CopilotProvider'

/**
 * Modal component for confirming AI-proposed schedule changes
 * Shows before the AI makes changes to the user's schedule
 */
export default function ScheduleConfirmation() {
    const { pendingScheduleChanges, confirmScheduleChanges, cancelScheduleChanges } = useCopilotContext()

    if (pendingScheduleChanges.length === 0) {
        return null
    }

    const formatTime = (time: string) => {
        const [hours, mins] = time.split(':')
        const h = parseInt(hours)
        const ampm = h >= 12 ? 'PM' : 'AM'
        const hour12 = h % 12 || 12
        return `${hour12}:${mins} ${ampm}`
    }

    const getChangeIcon = (type: string) => {
        switch (type) {
            case 'add':
                return (
                    <div className="w-8 h-8 rounded-lg bg-green-500/20 flex items-center justify-center">
                        <svg className="w-4 h-4 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                        </svg>
                    </div>
                )
            case 'move':
                return (
                    <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center">
                        <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                        </svg>
                    </div>
                )
            case 'delete':
                return (
                    <div className="w-8 h-8 rounded-lg bg-red-500/20 flex items-center justify-center">
                        <svg className="w-4 h-4 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                    </div>
                )
            default:
                return null
        }
    }

    const getChangeLabel = (type: string) => {
        switch (type) {
            case 'add':
                return 'New Task'
            case 'move':
                return 'Reschedule'
            case 'delete':
                return 'Remove'
            default:
                return type
        }
    }

    const getChangeColor = (type: string) => {
        switch (type) {
            case 'add':
                return 'text-green-400'
            case 'move':
                return 'text-blue-400'
            case 'delete':
                return 'text-red-400'
            default:
                return 'text-zinc-400'
        }
    }

    return (
        <>
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
                onClick={cancelScheduleChanges}
            />

            {/* Modal */}
            <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg glass rounded-2xl z-50 overflow-hidden">
                {/* Header */}
                <div className="px-6 py-4 border-b border-white/10 bg-surface-light/50">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center">
                            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                            </svg>
                        </div>
                        <div>
                            <h3 className="text-lg font-semibold text-white">Confirm Schedule Changes</h3>
                            <p className="text-sm text-zinc-400">
                                {pendingScheduleChanges.length} change{pendingScheduleChanges.length !== 1 ? 's' : ''} proposed
                            </p>
                        </div>
                    </div>
                </div>

                {/* Changes List */}
                <div className="p-6 max-h-[50vh] overflow-y-auto space-y-3">
                    {pendingScheduleChanges.map((change, index) => (
                        <div
                            key={index}
                            className="p-4 rounded-xl bg-surface-light border border-white/5"
                        >
                            <div className="flex items-start gap-3">
                                {getChangeIcon(change.type)}
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className={`text-xs font-medium ${getChangeColor(change.type)}`}>
                                            {getChangeLabel(change.type)}
                                        </span>
                                        {change.task.subject && (
                                            <span className="text-xs px-2 py-0.5 rounded bg-primary/20 text-primary">
                                                {change.task.subject}
                                            </span>
                                        )}
                                    </div>
                                    <h4 className="font-medium text-white truncate">
                                        {change.task.title}
                                    </h4>

                                    {/* Time details */}
                                    {change.type === 'add' && change.to && (
                                        <p className="text-sm text-zinc-400 mt-1">
                                            Scheduled for {formatTime(change.to.start)} - {formatTime(change.to.end)}
                                        </p>
                                    )}
                                    {change.type === 'move' && change.from && change.to && (
                                        <div className="text-sm text-zinc-400 mt-1 flex items-center gap-2">
                                            <span>{formatTime(change.from.start)} - {formatTime(change.from.end)}</span>
                                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                                            </svg>
                                            <span className="text-blue-400">{formatTime(change.to.start)} - {formatTime(change.to.end)}</span>
                                        </div>
                                    )}
                                    {change.type === 'delete' && change.from && (
                                        <p className="text-sm text-zinc-400 mt-1 line-through">
                                            Was scheduled for {formatTime(change.from.start)} - {formatTime(change.from.end)}
                                        </p>
                                    )}

                                    {/* Reason */}
                                    {change.reason && (
                                        <p className="text-xs text-zinc-500 mt-2 italic">
                                            Reason: {change.reason}
                                        </p>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>

                {/* Summary */}
                <div className="px-6 py-3 bg-surface-light/30 border-t border-white/5">
                    <div className="flex items-center gap-4 text-sm">
                        {pendingScheduleChanges.filter(c => c.type === 'add').length > 0 && (
                            <span className="text-green-400">
                                +{pendingScheduleChanges.filter(c => c.type === 'add').length} new
                            </span>
                        )}
                        {pendingScheduleChanges.filter(c => c.type === 'move').length > 0 && (
                            <span className="text-blue-400">
                                {pendingScheduleChanges.filter(c => c.type === 'move').length} moved
                            </span>
                        )}
                        {pendingScheduleChanges.filter(c => c.type === 'delete').length > 0 && (
                            <span className="text-red-400">
                                -{pendingScheduleChanges.filter(c => c.type === 'delete').length} removed
                            </span>
                        )}
                    </div>
                </div>

                {/* Actions */}
                <div className="px-6 py-4 border-t border-white/10 flex gap-3">
                    <button
                        onClick={cancelScheduleChanges}
                        className="flex-1 py-3 rounded-xl bg-surface-light text-zinc-400 hover:text-white font-medium transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={confirmScheduleChanges}
                        className="flex-1 py-3 rounded-xl gradient-primary text-white font-medium hover:opacity-90 transition-opacity"
                    >
                        Apply Changes
                    </button>
                </div>
            </div>
        </>
    )
}
