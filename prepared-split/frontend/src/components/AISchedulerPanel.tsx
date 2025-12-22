'use client'

import { useState, useCallback } from 'react'
import { 
    Sparkles, 
    Zap, 
    Clock, 
    Target, 
    TrendingUp, 
    Brain,
    RefreshCw,
    CheckCircle2,
    AlertTriangle,
    Calendar,
    Settings2
} from 'lucide-react'

interface OptimizationResult {
    success: boolean
    status: string
    optimized_tasks: Array<{
        id: number
        title: string
        assigned_slot: number
        priority: number
    }>
    gaps_filled: number
    conflicts: number
    execution_time_ms: number
    message: string
}

interface ScheduleGap {
    date: string
    day_name: string
    start_time: string
    end_time: string
    duration_minutes: number
    gap_type: 'micro' | 'standard' | 'deep_work'
}

interface GapAnalysis {
    micro: ScheduleGap[]
    standard: ScheduleGap[]
    deep_work: ScheduleGap[]
    summary: {
        micro_count: number
        standard_count: number
        deep_work_count: number
        total_deep_work_mins: number
    }
}

interface ProgressSummary {
    metrics: Array<{
        type: string
        current: number
        previous: number
        trend_direction: 'up' | 'down' | 'stable'
        trend_percentage: number
    }>
    insights: string[]
    achievements: string[]
    warnings: string[]
    recommendations: string[]
}

export default function AISchedulerPanel() {
    const [isOptimizing, setIsOptimizing] = useState(false)
    const [optimizationResult, setOptimizationResult] = useState<OptimizationResult | null>(null)
    const [gaps, setGaps] = useState<GapAnalysis | null>(null)
    const [progress, setProgress] = useState<ProgressSummary | null>(null)
    const [activePanel, setActivePanel] = useState<'optimize' | 'gaps' | 'progress'>('optimize')
    const [showSettings, setShowSettings] = useState(false)

    // Settings state
    const [settings, setSettings] = useState({
        includeConceptTasks: true,
        includePracticeTasks: true,
        respectEnergyLevels: true
    })

    const optimizeSchedule = useCallback(async () => {
        setIsOptimizing(true)
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: `optimize_weekly_timeline with include_concept_tasks=${settings.includeConceptTasks} include_practice_tasks=${settings.includePracticeTasks} respect_energy_levels=${settings.respectEnergyLevels}`,
                    use_tools: true,
                    tool_name: 'optimize_weekly_timeline',
                    tool_args: {
                        include_concept_tasks: settings.includeConceptTasks,
                        include_practice_tasks: settings.includePracticeTasks,
                        respect_energy_levels: settings.respectEnergyLevels
                    }
                })
            })
            
            if (response.ok) {
                const data = await response.json()
                setOptimizationResult(data.tool_result || data)
            }
        } catch (error) {
            console.error('Optimization failed:', error)
        } finally {
            setIsOptimizing(false)
        }
    }, [settings])

    const analyzeGaps = useCallback(async () => {
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: 'get_schedule_gaps days_ahead=7',
                    use_tools: true,
                    tool_name: 'get_schedule_gaps',
                    tool_args: { days_ahead: 7 }
                })
            })
            
            if (response.ok) {
                const data = await response.json()
                setGaps(data.tool_result?.gaps || data.gaps)
            }
        } catch (error) {
            console.error('Gap analysis failed:', error)
        }
    }, [])

    const fetchProgress = useCallback(async () => {
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: 'get_progress_summary period=this_week',
                    use_tools: true,
                    tool_name: 'get_progress_summary',
                    tool_args: { period: 'this_week' }
                })
            })
            
            if (response.ok) {
                const data = await response.json()
                setProgress(data.tool_result || data)
            }
        } catch (error) {
            console.error('Progress fetch failed:', error)
        }
    }, [])

    const renderOptimizePanel = () => (
        <div className="space-y-6">
            {/* Quick Actions */}
            <div className="grid grid-cols-2 gap-3">
                <button
                    onClick={optimizeSchedule}
                    disabled={isOptimizing}
                    className="flex items-center justify-center gap-2 p-4 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-medium transition-all disabled:opacity-50"
                >
                    {isOptimizing ? (
                        <RefreshCw className="w-5 h-5 animate-spin" />
                    ) : (
                        <Sparkles className="w-5 h-5" />
                    )}
                    {isOptimizing ? 'Optimizing...' : 'Optimize Week'}
                </button>
                
                <button
                    onClick={() => setShowSettings(!showSettings)}
                    className="flex items-center justify-center gap-2 p-4 rounded-xl bg-surface-light hover:bg-surface text-zinc-300 font-medium transition-all"
                >
                    <Settings2 className="w-5 h-5" />
                    Settings
                </button>
            </div>

            {/* Settings Panel */}
            {showSettings && (
                <div className="p-4 rounded-xl bg-surface-light/50 space-y-3">
                    <h4 className="text-sm font-medium text-zinc-400 mb-3">Optimization Options</h4>
                    
                    <label className="flex items-center gap-3 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={settings.includeConceptTasks}
                            onChange={(e) => setSettings(s => ({ ...s, includeConceptTasks: e.target.checked }))}
                            className="w-4 h-4 rounded border-zinc-600 text-indigo-600 focus:ring-indigo-500"
                        />
                        <span className="text-sm text-zinc-300">Include concept study (morning priority)</span>
                    </label>

                    <label className="flex items-center gap-3 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={settings.includePracticeTasks}
                            onChange={(e) => setSettings(s => ({ ...s, includePracticeTasks: e.target.checked }))}
                            className="w-4 h-4 rounded border-zinc-600 text-indigo-600 focus:ring-indigo-500"
                        />
                        <span className="text-sm text-zinc-300">Include practice tasks (evening priority)</span>
                    </label>

                    <label className="flex items-center gap-3 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={settings.respectEnergyLevels}
                            onChange={(e) => setSettings(s => ({ ...s, respectEnergyLevels: e.target.checked }))}
                            className="w-4 h-4 rounded border-zinc-600 text-indigo-600 focus:ring-indigo-500"
                        />
                        <span className="text-sm text-zinc-300">Respect daily energy patterns</span>
                    </label>
                </div>
            )}

            {/* Optimization Result */}
            {optimizationResult && (
                <div className={`p-4 rounded-xl ${optimizationResult.success ? 'bg-green-500/10 border border-green-500/30' : 'bg-yellow-500/10 border border-yellow-500/30'}`}>
                    <div className="flex items-center gap-2 mb-3">
                        {optimizationResult.success ? (
                            <CheckCircle2 className="w-5 h-5 text-green-400" />
                        ) : (
                            <AlertTriangle className="w-5 h-5 text-yellow-400" />
                        )}
                        <span className="font-medium text-white">
                            {optimizationResult.success ? 'Optimization Complete' : 'Partial Optimization'}
                        </span>
                    </div>
                    
                    <p className="text-sm text-zinc-400 mb-3">{optimizationResult.message}</p>
                    
                    <div className="grid grid-cols-3 gap-3 text-center">
                        <div className="p-2 rounded-lg bg-white/5">
                            <p className="text-lg font-bold text-green-400">{optimizationResult.gaps_filled}</p>
                            <p className="text-xs text-zinc-500">Tasks Placed</p>
                        </div>
                        <div className="p-2 rounded-lg bg-white/5">
                            <p className="text-lg font-bold text-yellow-400">{optimizationResult.conflicts}</p>
                            <p className="text-xs text-zinc-500">Conflicts</p>
                        </div>
                        <div className="p-2 rounded-lg bg-white/5">
                            <p className="text-lg font-bold text-blue-400">{optimizationResult.execution_time_ms.toFixed(0)}ms</p>
                            <p className="text-xs text-zinc-500">Time</p>
                        </div>
                    </div>
                </div>
            )}

            {/* Quick Insights */}
            <div className="space-y-3">
                <h4 className="text-sm font-medium text-zinc-400">AI Scheduling Features</h4>
                
                <div className="flex items-center gap-3 p-3 rounded-lg bg-surface-light/50">
                    <div className="p-2 rounded-lg bg-indigo-500/20">
                        <Brain className="w-4 h-4 text-indigo-400" />
                    </div>
                    <div className="flex-1">
                        <p className="text-sm font-medium text-white">Energy-Aware Placement</p>
                        <p className="text-xs text-zinc-500">Concepts → morning, Practice → evening</p>
                    </div>
                </div>

                <div className="flex items-center gap-3 p-3 rounded-lg bg-surface-light/50">
                    <div className="p-2 rounded-lg bg-purple-500/20">
                        <Zap className="w-4 h-4 text-purple-400" />
                    </div>
                    <div className="flex-1">
                        <p className="text-sm font-medium text-white">Micro-Gap Filling</p>
                        <p className="text-xs text-zinc-500">15-30 min gaps for quick reviews</p>
                    </div>
                </div>

                <div className="flex items-center gap-3 p-3 rounded-lg bg-surface-light/50">
                    <div className="p-2 rounded-lg bg-green-500/20">
                        <Target className="w-4 h-4 text-green-400" />
                    </div>
                    <div className="flex-1">
                        <p className="text-sm font-medium text-white">Deadline-Aware</p>
                        <p className="text-xs text-zinc-500">Priority tasks scheduled first</p>
                    </div>
                </div>
            </div>
        </div>
    )

    const renderGapsPanel = () => (
        <div className="space-y-4">
            <button
                onClick={analyzeGaps}
                className="w-full flex items-center justify-center gap-2 p-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-medium transition-all"
            >
                <Clock className="w-5 h-5" />
                Analyze Gaps
            </button>

            {gaps && (
                <div className="space-y-4">
                    {/* Summary */}
                    <div className="grid grid-cols-3 gap-3">
                        <div className="p-3 rounded-xl bg-orange-500/10 border border-orange-500/30 text-center">
                            <p className="text-2xl font-bold text-orange-400">{gaps.summary?.micro_count || 0}</p>
                            <p className="text-xs text-zinc-500">Micro</p>
                            <p className="text-xs text-zinc-600">&lt;30min</p>
                        </div>
                        <div className="p-3 rounded-xl bg-blue-500/10 border border-blue-500/30 text-center">
                            <p className="text-2xl font-bold text-blue-400">{gaps.summary?.standard_count || 0}</p>
                            <p className="text-xs text-zinc-500">Standard</p>
                            <p className="text-xs text-zinc-600">30-60min</p>
                        </div>
                        <div className="p-3 rounded-xl bg-green-500/10 border border-green-500/30 text-center">
                            <p className="text-2xl font-bold text-green-400">{gaps.summary?.deep_work_count || 0}</p>
                            <p className="text-xs text-zinc-500">Deep Work</p>
                            <p className="text-xs text-zinc-600">&gt;60min</p>
                        </div>
                    </div>

                    {/* Deep Work Opportunities */}
                    {gaps.deep_work && gaps.deep_work.length > 0 && (
                        <div className="space-y-2">
                            <h4 className="text-sm font-medium text-green-400 flex items-center gap-2">
                                <Target className="w-4 h-4" />
                                Deep Work Opportunities
                            </h4>
                            {gaps.deep_work.slice(0, 3).map((gap, i) => (
                                <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-green-500/5 border border-green-500/20">
                                    <Calendar className="w-4 h-4 text-green-400" />
                                    <div className="flex-1">
                                        <p className="text-sm font-medium text-white">{gap.day_name}</p>
                                        <p className="text-xs text-zinc-500">{gap.start_time} - {gap.end_time}</p>
                                    </div>
                                    <span className="text-sm font-medium text-green-400">{gap.duration_minutes}min</span>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Total Deep Work */}
                    <div className="p-4 rounded-xl bg-gradient-to-r from-green-500/10 to-emerald-500/10 border border-green-500/20">
                        <p className="text-sm text-zinc-400">Total Deep Work Available</p>
                        <p className="text-3xl font-bold text-green-400">
                            {Math.round((gaps.summary?.total_deep_work_mins || 0) / 60)}h {(gaps.summary?.total_deep_work_mins || 0) % 60}m
                        </p>
                    </div>
                </div>
            )}
        </div>
    )

    const renderProgressPanel = () => (
        <div className="space-y-4">
            <button
                onClick={fetchProgress}
                className="w-full flex items-center justify-center gap-2 p-3 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-medium transition-all"
            >
                <TrendingUp className="w-5 h-5" />
                Get Progress
            </button>

            {progress && (
                <div className="space-y-4">
                    {/* Metrics */}
                    {progress.metrics && progress.metrics.length > 0 && (
                        <div className="space-y-2">
                            {progress.metrics.map((metric, i) => (
                                <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-surface-light/50">
                                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                                        metric.trend_direction === 'up' ? 'bg-green-500/20' :
                                        metric.trend_direction === 'down' ? 'bg-red-500/20' : 'bg-zinc-500/20'
                                    }`}>
                                        <TrendingUp className={`w-4 h-4 ${
                                            metric.trend_direction === 'up' ? 'text-green-400' :
                                            metric.trend_direction === 'down' ? 'text-red-400 rotate-180' : 'text-zinc-400'
                                        }`} />
                                    </div>
                                    <div className="flex-1">
                                        <p className="text-sm font-medium text-white capitalize">
                                            {metric.type.replace(/_/g, ' ')}
                                        </p>
                                        <p className="text-xs text-zinc-500">
                                            {metric.trend_direction === 'up' ? '+' : metric.trend_direction === 'down' ? '-' : ''}
                                            {metric.trend_percentage}% from last period
                                        </p>
                                    </div>
                                    <span className="text-lg font-bold text-white">{metric.current}</span>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Achievements */}
                    {progress.achievements && progress.achievements.length > 0 && (
                        <div className="space-y-2">
                            <h4 className="text-sm font-medium text-yellow-400">🌟 Achievements</h4>
                            {progress.achievements.map((achievement, i) => (
                                <div key={i} className="p-2 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                                    <p className="text-sm text-yellow-200">{achievement}</p>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Warnings */}
                    {progress.warnings && progress.warnings.length > 0 && (
                        <div className="space-y-2">
                            <h4 className="text-sm font-medium text-orange-400">⚠️ Attention Needed</h4>
                            {progress.warnings.map((warning, i) => (
                                <div key={i} className="p-2 rounded-lg bg-orange-500/10 border border-orange-500/20">
                                    <p className="text-sm text-orange-200">{warning}</p>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Recommendations */}
                    {progress.recommendations && progress.recommendations.length > 0 && (
                        <div className="space-y-2">
                            <h4 className="text-sm font-medium text-blue-400">💡 Recommendations</h4>
                            {progress.recommendations.map((rec, i) => (
                                <div key={i} className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/20">
                                    <p className="text-sm text-blue-200">{rec}</p>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    )

    return (
        <div className="glass rounded-2xl overflow-hidden">
            {/* Header */}
            <div className="p-4 border-b border-white/10 bg-gradient-to-r from-indigo-600/20 to-purple-600/20">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-500 flex items-center justify-center">
                        <Brain className="w-5 h-5 text-white" />
                    </div>
                    <div>
                        <h3 className="font-semibold text-white">AI Scheduler</h3>
                        <p className="text-xs text-zinc-400">Constraint Satisfaction Engine</p>
                    </div>
                </div>
            </div>

            {/* Tab Navigation */}
            <div className="flex border-b border-white/10">
                {[
                    { id: 'optimize' as const, label: 'Optimize', icon: Sparkles },
                    { id: 'gaps' as const, label: 'Gaps', icon: Clock },
                    { id: 'progress' as const, label: 'Progress', icon: TrendingUp }
                ].map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActivePanel(tab.id)}
                        className={`flex-1 flex items-center justify-center gap-2 p-3 text-sm font-medium transition-colors ${
                            activePanel === tab.id
                                ? 'text-white bg-white/5 border-b-2 border-indigo-500'
                                : 'text-zinc-500 hover:text-zinc-300'
                        }`}
                    >
                        <tab.icon className="w-4 h-4" />
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Panel Content */}
            <div className="p-4">
                {activePanel === 'optimize' && renderOptimizePanel()}
                {activePanel === 'gaps' && renderGapsPanel()}
                {activePanel === 'progress' && renderProgressPanel()}
            </div>
        </div>
    )
}
