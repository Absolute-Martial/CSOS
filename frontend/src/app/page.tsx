'use client'

import { useEffect, useState } from 'react'
import Dashboard from '@/components/Dashboard'
import AICommandCenter from '@/components/AICommandCenter'
import AISchedulerPanel from '@/components/AISchedulerPanel'
import SettingsPanel from '@/components/SettingsPanel'
import SystemBadge from '@/components/SystemBadge'
import StudyTimer from '@/components/StudyTimer'
import TodayDashboard from '@/components/TodayDashboard'
import TimelineView from '@/components/TimelineView'
import ScheduleInput from '@/components/ScheduleInput'
import LabReportTracker from '@/components/LabReportTracker'
import StudyAnalytics from '@/components/StudyAnalytics'
import GoalTracker from '@/components/GoalTracker'

type TabType = 'today' | 'timeline' | 'tasks' | 'labs' | 'analytics' | 'goals' | 'ai-scheduler' | 'settings'

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
    const [activeTab, setActiveTab] = useState<TabType>('today')

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

    const tabs = [
        { id: 'today' as TabType, label: 'Today', icon: '📊' },
        { id: 'timeline' as TabType, label: 'Timeline', icon: '📅' },
        { id: 'ai-scheduler' as TabType, label: 'AI Scheduler', icon: '🧠' },
        { id: 'tasks' as TabType, label: 'Tasks', icon: '✅' },
        { id: 'labs' as TabType, label: 'Labs', icon: '🧪' },
        { id: 'analytics' as TabType, label: 'Analytics', icon: '📈' },
        { id: 'goals' as TabType, label: 'Goals', icon: '🎯' },
        { id: 'settings' as TabType, label: 'Settings', icon: '⚙️' },
    ]


    const renderTabContent = () => {
        switch (activeTab) {
            case 'today':
                return <TodayDashboard />
            case 'timeline':
                return (
                    <div className="space-y-6">
                        <ScheduleInput onScheduleChange={() => { }} />
                        <TimelineView />
                    </div>
                )
            case 'ai-scheduler':
                return <AISchedulerPanel />
            case 'tasks':
                return <Dashboard />
            case 'labs':
                return <LabReportTracker />
            case 'analytics':
                return <StudyAnalytics />
            case 'goals':
                return <GoalTracker />
            case 'settings':
                return <SettingsPanel />
            default:
                return <TodayDashboard />
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
                            {/* Study Timer */}
                            <StudyTimer />

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

            {/* Tab Navigation */}
            <div className="bg-surface border-b border-white/10">
                <div className="max-w-7xl mx-auto px-6">
                    <div className="flex gap-1 overflow-x-auto py-2">
                        {tabs.map(tab => (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors whitespace-nowrap ${activeTab === tab.id
                                    ? 'bg-primary text-white'
                                    : 'text-zinc-400 hover:text-white hover:bg-surface-light'
                                    }`}
                            >
                                <span>{tab.icon}</span>
                                <span className="text-sm font-medium">{tab.label}</span>
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 max-w-7xl mx-auto w-full px-6 py-8">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Left: Tab Content */}
                    <div className="lg:col-span-2 space-y-6">
                        {/* Greeting Card */}
                        {briefing && activeTab === 'today' && (
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

                        {renderTabContent()}
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