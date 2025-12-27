'use client'

import { useEffect, useState } from 'react'

interface FocusScoreData {
    score: number
    maxScore: number
    breakdown: {
        deepWorkRatio: number      // 0-30 points
        streakBonus: number        // 0-20 points
        goalProgress: number       // 0-25 points
        consistencyBonus: number   // 0-15 points
        pomodoroBonus: number      // 0-10 points
    }
    trend: 'up' | 'down' | 'stable'
    previousScore: number
}

export default function FocusScore() {
    const [data, setData] = useState<FocusScoreData | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetchFocusScore()
    }, [])

    const fetchFocusScore = async () => {
        try {
            // TODO: Replace with actual API call when backend is ready
            // const res = await fetch('/api/focus-score')
            // const data = await res.json()

            // Mock data for now
            const mockData: FocusScoreData = {
                score: 72,
                maxScore: 100,
                breakdown: {
                    deepWorkRatio: 22,
                    streakBonus: 15,
                    goalProgress: 18,
                    consistencyBonus: 10,
                    pomodoroBonus: 7,
                },
                trend: 'up',
                previousScore: 65,
            }

            setData(mockData)
        } catch (error) {
            console.error('Failed to fetch focus score:', error)
        } finally {
            setLoading(false)
        }
    }

    if (loading) {
        return (
            <div className="glass rounded-2xl p-4 animate-pulse">
                <div className="h-4 bg-surface-light rounded w-24 mb-2"></div>
                <div className="h-16 bg-surface-light rounded"></div>
            </div>
        )
    }

    if (!data) return null

    const percentage = (data.score / data.maxScore) * 100
    const scoreDiff = data.score - data.previousScore

    const getScoreColor = () => {
        if (data.score >= 80) return 'text-green-400'
        if (data.score >= 60) return 'text-primary'
        if (data.score >= 40) return 'text-yellow-400'
        return 'text-red-400'
    }

    const getGradeLabel = () => {
        if (data.score >= 90) return { grade: 'S', label: 'Exceptional' }
        if (data.score >= 80) return { grade: 'A', label: 'Excellent' }
        if (data.score >= 70) return { grade: 'B', label: 'Good' }
        if (data.score >= 60) return { grade: 'C', label: 'Fair' }
        if (data.score >= 50) return { grade: 'D', label: 'Needs Work' }
        return { grade: 'F', label: 'Keep Trying' }
    }

    const { grade, label } = getGradeLabel()

    return (
        <div className="glass rounded-2xl p-4">
            <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-medium text-zinc-400">Focus Score</h3>
                <div className={`flex items-center gap-1 text-xs ${data.trend === 'up' ? 'text-green-400' : data.trend === 'down' ? 'text-red-400' : 'text-zinc-400'
                    }`}>
                    {data.trend === 'up' && (
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
                        </svg>
                    )}
                    {data.trend === 'down' && (
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                        </svg>
                    )}
                    <span>{scoreDiff > 0 ? '+' : ''}{scoreDiff} from yesterday</span>
                </div>
            </div>

            {/* Main score display */}
            <div className="flex items-center gap-4">
                <div className="relative">
                    {/* Circular progress */}
                    <svg className="w-20 h-20 -rotate-90">
                        <circle
                            cx="40"
                            cy="40"
                            r="36"
                            fill="none"
                            stroke="rgba(255,255,255,0.1)"
                            strokeWidth="6"
                        />
                        <circle
                            cx="40"
                            cy="40"
                            r="36"
                            fill="none"
                            stroke="url(#focusGradient)"
                            strokeWidth="6"
                            strokeLinecap="round"
                            strokeDasharray={2 * Math.PI * 36}
                            strokeDashoffset={2 * Math.PI * 36 * (1 - percentage / 100)}
                            className="transition-all duration-1000"
                        />
                        <defs>
                            <linearGradient id="focusGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                                <stop offset="0%" stopColor="#42D674" />
                                <stop offset="100%" stopColor="#80EF80" />
                            </linearGradient>
                        </defs>
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                        <span className={`text-2xl font-bold ${getScoreColor()}`}>{data.score}</span>
                    </div>
                </div>

                <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                        <span className={`text-2xl font-bold ${getScoreColor()}`}>{grade}</span>
                        <span className="text-sm text-zinc-400">{label}</span>
                    </div>

                    {/* Mini breakdown bars */}
                    <div className="space-y-1">
                        <div className="flex items-center gap-2 text-xs">
                            <span className="text-zinc-500 w-16">Deep Work</span>
                            <div className="flex-1 h-1.5 bg-surface-light rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-primary rounded-full transition-all"
                                    style={{ width: `${(data.breakdown.deepWorkRatio / 30) * 100}%` }}
                                />
                            </div>
                        </div>
                        <div className="flex items-center gap-2 text-xs">
                            <span className="text-zinc-500 w-16">Goals</span>
                            <div className="flex-1 h-1.5 bg-surface-light rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-secondary rounded-full transition-all"
                                    style={{ width: `${(data.breakdown.goalProgress / 25) * 100}%` }}
                                />
                            </div>
                        </div>
                        <div className="flex items-center gap-2 text-xs">
                            <span className="text-zinc-500 w-16">Streak</span>
                            <div className="flex-1 h-1.5 bg-surface-light rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-accent rounded-full transition-all"
                                    style={{ width: `${(data.breakdown.streakBonus / 20) * 100}%` }}
                                />
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
