'use client'

import { useEffect, useState } from 'react'
import Dashboard from '@/components/Dashboard'
import AICommandCenter from '@/components/AICommandCenter'
import SystemBadge from '@/components/SystemBadge'

interface Briefing {
    greeting: string
    current_streak: number
    streak_icon: string
    tasks_today: number
    revisions_due: number
    deep_work_available: number
    unread_notifications: number
}

export default function Home() {
    const [briefing, setBriefing] = useState<Briefing | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetchBriefing()
    }, [])

    const fetchBriefing = async () => {
        try {
            const res = await fetch('/api/briefing')
            if (res.ok) {
                const data = await res.json()
                setBriefing(data)
            }
        } catch (error) {
            console.error('Failed to fetch briefing:', error)
        } finally {
            setLoading(false)
        }
    }

    return (
        <main className="flex-1 flex flex-col">
            {/* Header */}
            <header className="glass sticky top-0 z-50 px-6 py-4 border-b border-white/10">
                <div className="max-w-7xl mx-auto flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center">
                            <span className="text-xl">⚡</span>
                        </div>
                        <div>
                            <h1 className="text-xl font-bold text-white">Engineering OS</h1>
                            <p className="text-sm text-zinc-400">KU Computer Science</p>
                        </div>
                    </div>

                    {briefing && (
                        <div className="flex items-center gap-6">
                            {/* Streak */}
                            <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-surface-light">
                                <span className="text-2xl streak-fire">🔥</span>
                                <div>
                                    <p className="text-sm font-medium text-white">{briefing.current_streak} days</p>
                                    <p className="text-xs text-zinc-400">Current streak</p>
                                </div>
                            </div>

                            {/* Notifications */}
                            {briefing.unread_notifications > 0 && (
                                <button className="relative p-2 rounded-lg bg-surface-light hover:bg-surface transition">
                                    <span className="text-xl">🔔</span>
                                    <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-red-500 text-xs flex items-center justify-center notification-badge">
                                        {briefing.unread_notifications}
                                    </span>
                                </button>
                            )}
                        </div>
                    )}
                </div>
            </header>

            {/* Main Content */}
            <div className="flex-1 max-w-7xl mx-auto w-full px-6 py-8">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Left: Dashboard */}
                    <div className="lg:col-span-2 space-y-6">
                        {/* Greeting */}
                        {briefing && (
                            <div className="glass rounded-2xl p-6 card-hover">
                                <h2 className="text-2xl font-bold text-white mb-2">
                                    {briefing.greeting}
                                </h2>
                                <div className="grid grid-cols-3 gap-4 mt-4">
                                    <div className="text-center p-4 rounded-xl bg-primary/20">
                                        <p className="text-3xl font-bold text-primary">{briefing.tasks_today}</p>
                                        <p className="text-sm text-zinc-400">Tasks Today</p>
                                    </div>
                                    <div className="text-center p-4 rounded-xl bg-blue-500/20">
                                        <p className="text-3xl font-bold text-blue-400">{briefing.revisions_due}</p>
                                        <p className="text-sm text-zinc-400">Revisions Due</p>
                                    </div>
                                    <div className="text-center p-4 rounded-xl bg-green-500/20">
                                        <p className="text-3xl font-bold text-green-400">{Math.round(briefing.deep_work_available / 60)}h</p>
                                        <p className="text-sm text-zinc-400">Deep Work</p>
                                    </div>
                                </div>
                            </div>
                        )}

                        <Dashboard />
                    </div>

                    {/* Right: AI Command Center */}
                    <div className="lg:col-span-1">
                        <AICommandCenter />
                    </div>
                </div>
            </div>

            {/* Footer with System Badge */}
            <SystemBadge />
        </main>
    )
}
