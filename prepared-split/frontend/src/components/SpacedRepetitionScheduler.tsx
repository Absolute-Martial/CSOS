'use client'

import { useState, useEffect } from 'react'

interface ReviewItem {
    id: number
    chapter_id: number
    chapter_title: string
    subject_code: string
    subject_name: string
    color: string
    due_date: string
    days_until_due: number
    ease_factor: number
    interval_days: number
    repetitions: number
    last_reviewed?: string
}

interface SpacedRepetitionData {
    due_today: ReviewItem[]
    upcoming: ReviewItem[]
    overdue: ReviewItem[]
    stats: {
        total_chapters: number
        mastered: number
        learning: number
        new: number
    }
}

// SM-2 Algorithm rating
type Rating = 0 | 1 | 2 | 3 | 4 | 5

const RATING_LABELS: Record<Rating, { label: string; color: string }> = {
    0: { label: 'Complete Blackout', color: 'text-red-500' },
    1: { label: 'Incorrect', color: 'text-red-400' },
    2: { label: 'Almost', color: 'text-orange-400' },
    3: { label: 'Correct with Difficulty', color: 'text-yellow-400' },
    4: { label: 'Correct', color: 'text-green-400' },
    5: { label: 'Perfect', color: 'text-emerald-400' },
}

export default function SpacedRepetitionScheduler() {
    const [data, setData] = useState<SpacedRepetitionData | null>(null)
    const [loading, setLoading] = useState(true)
    const [activeReview, setActiveReview] = useState<ReviewItem | null>(null)
    const [showRating, setShowRating] = useState(false)

    useEffect(() => {
        fetchReviewData()
    }, [])

    const fetchReviewData = async () => {
        try {
            // TODO: Replace with actual API call
            // const res = await fetch('/api/spaced-repetition/due')
            // const data = await res.json()

            // Mock data
            const mockData: SpacedRepetitionData = {
                due_today: [
                    {
                        id: 1,
                        chapter_id: 5,
                        chapter_title: 'Binary Search Trees',
                        subject_code: 'COMP202',
                        subject_name: 'Data Structures',
                        color: '#3b82f6',
                        due_date: new Date().toISOString(),
                        days_until_due: 0,
                        ease_factor: 2.5,
                        interval_days: 4,
                        repetitions: 2,
                        last_reviewed: new Date(Date.now() - 4 * 24 * 60 * 60 * 1000).toISOString(),
                    },
                    {
                        id: 2,
                        chapter_id: 3,
                        chapter_title: 'Newton\'s Laws',
                        subject_code: 'PHYS101',
                        subject_name: 'Physics I',
                        color: '#ef4444',
                        due_date: new Date().toISOString(),
                        days_until_due: 0,
                        ease_factor: 2.3,
                        interval_days: 2,
                        repetitions: 1,
                    },
                ],
                upcoming: [
                    {
                        id: 3,
                        chapter_id: 7,
                        chapter_title: 'Organic Reactions',
                        subject_code: 'CHEM101',
                        subject_name: 'Chemistry I',
                        color: '#22c55e',
                        due_date: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString(),
                        days_until_due: 2,
                        ease_factor: 2.6,
                        interval_days: 7,
                        repetitions: 3,
                    },
                ],
                overdue: [],
                stats: {
                    total_chapters: 24,
                    mastered: 8,
                    learning: 12,
                    new: 4,
                },
            }

            setData(mockData)
        } catch (error) {
            console.error('Failed to fetch review data:', error)
        } finally {
            setLoading(false)
        }
    }

    const handleReview = async (rating: Rating) => {
        if (!activeReview) return

        try {
            // TODO: Replace with actual API call
            // await fetch(`/api/spaced-repetition/${activeReview.id}/review`, {
            //     method: 'POST',
            //     headers: { 'Content-Type': 'application/json' },
            //     body: JSON.stringify({ rating })
            // })

            console.log(`Reviewed ${activeReview.chapter_title} with rating ${rating}`)

            // Remove from due_today list
            setData(prev => {
                if (!prev) return null
                return {
                    ...prev,
                    due_today: prev.due_today.filter(item => item.id !== activeReview.id),
                }
            })

            setActiveReview(null)
            setShowRating(false)
        } catch (error) {
            console.error('Failed to submit review:', error)
        }
    }

    const startReview = (item: ReviewItem) => {
        setActiveReview(item)
        setShowRating(false)
    }

    if (loading) {
        return (
            <div className="glass rounded-2xl p-6 animate-pulse">
                <div className="h-6 bg-surface-light rounded w-1/3 mb-4"></div>
                <div className="space-y-3">
                    {[1, 2, 3].map(i => (
                        <div key={i} className="h-16 bg-surface-light rounded-xl"></div>
                    ))}
                </div>
            </div>
        )
    }

    if (!data) return null

    // Active review UI
    if (activeReview) {
        return (
            <div className="glass rounded-2xl p-6">
                <div className="text-center mb-6">
                    <span
                        className="inline-block px-3 py-1 rounded-lg text-sm font-medium text-white mb-2"
                        style={{ backgroundColor: activeReview.color }}
                    >
                        {activeReview.subject_code}
                    </span>
                    <h2 className="text-2xl font-bold text-white">{activeReview.chapter_title}</h2>
                    <p className="text-sm text-zinc-400 mt-1">{activeReview.subject_name}</p>
                </div>

                {!showRating ? (
                    <div className="text-center space-y-4">
                        <p className="text-zinc-300">
                            Review this chapter, then rate your recall.
                        </p>
                        <button
                            onClick={() => setShowRating(true)}
                            className="px-6 py-3 rounded-xl gradient-primary text-white font-medium hover:opacity-90 transition"
                        >
                            Show Answer
                        </button>
                        <button
                            onClick={() => {
                                setActiveReview(null)
                                setShowRating(false)
                            }}
                            className="block w-full text-sm text-zinc-500 hover:text-zinc-300 transition"
                        >
                            Skip for now
                        </button>
                    </div>
                ) : (
                    <div className="space-y-4">
                        <p className="text-center text-zinc-300 mb-4">How well did you recall?</p>
                        <div className="grid grid-cols-2 gap-2">
                            {([0, 1, 2, 3, 4, 5] as Rating[]).map(rating => (
                                <button
                                    key={rating}
                                    onClick={() => handleReview(rating)}
                                    className={`p-3 rounded-lg bg-surface-light hover:bg-white/10 transition text-left ${RATING_LABELS[rating].color}`}
                                >
                                    <span className="font-bold">{rating}</span>
                                    <p className="text-xs text-zinc-400">{RATING_LABELS[rating].label}</p>
                                </button>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        )
    }

    return (
        <div className="glass rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                    <span className="text-xl">🧠</span> Spaced Repetition
                </h2>
                <div className="text-xs text-zinc-400">
                    {data.stats.mastered}/{data.stats.total_chapters} mastered
                </div>
            </div>

            {/* Stats bar */}
            <div className="flex gap-1 h-2 rounded-full overflow-hidden mb-4">
                <div
                    className="bg-emerald-500"
                    style={{ width: `${(data.stats.mastered / data.stats.total_chapters) * 100}%` }}
                />
                <div
                    className="bg-yellow-500"
                    style={{ width: `${(data.stats.learning / data.stats.total_chapters) * 100}%` }}
                />
                <div
                    className="bg-zinc-600"
                    style={{ width: `${(data.stats.new / data.stats.total_chapters) * 100}%` }}
                />
            </div>
            <div className="flex justify-between text-xs text-zinc-500 mb-4">
                <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-emerald-500"></span> Mastered
                </span>
                <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-yellow-500"></span> Learning
                </span>
                <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-zinc-600"></span> New
                </span>
            </div>

            {/* Due Today */}
            {data.due_today.length > 0 && (
                <div className="mb-4">
                    <h3 className="text-sm font-medium text-zinc-400 mb-2">
                        Due Today ({data.due_today.length})
                    </h3>
                    <div className="space-y-2">
                        {data.due_today.map(item => (
                            <div
                                key={item.id}
                                onClick={() => startReview(item)}
                                className="flex items-center gap-3 p-3 rounded-lg bg-primary/10 border border-primary/20 cursor-pointer hover:bg-primary/20 transition"
                            >
                                <div
                                    className="w-3 h-3 rounded-full"
                                    style={{ backgroundColor: item.color }}
                                />
                                <div className="flex-1 min-w-0">
                                    <p className="font-medium text-white truncate">{item.chapter_title}</p>
                                    <p className="text-xs text-zinc-400">{item.subject_code}</p>
                                </div>
                                <span className="text-xs px-2 py-1 rounded bg-primary/20 text-primary">
                                    Review
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* No reviews due */}
            {data.due_today.length === 0 && data.overdue.length === 0 && (
                <div className="text-center py-6">
                    <span className="text-4xl">🎉</span>
                    <p className="text-zinc-300 mt-2">All caught up!</p>
                    <p className="text-xs text-zinc-500">No reviews due today</p>
                </div>
            )}

            {/* Upcoming */}
            {data.upcoming.length > 0 && (
                <div>
                    <h3 className="text-sm font-medium text-zinc-400 mb-2">Coming Up</h3>
                    <div className="space-y-2">
                        {data.upcoming.slice(0, 3).map(item => (
                            <div
                                key={item.id}
                                className="flex items-center gap-3 p-2 rounded-lg bg-surface-light"
                            >
                                <div
                                    className="w-2 h-2 rounded-full"
                                    style={{ backgroundColor: item.color }}
                                />
                                <span className="flex-1 text-sm text-zinc-300 truncate">
                                    {item.chapter_title}
                                </span>
                                <span className="text-xs text-zinc-500">
                                    in {item.days_until_due}d
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}
