'use client'

import { useState, useEffect, useCallback } from 'react'

interface PomodoroTimerProps {
    onSessionComplete?: (type: 'work' | 'break') => void
}

const PRESETS = {
    classic: { work: 25, shortBreak: 5, longBreak: 15, sessionsBeforeLong: 4 },
    short: { work: 15, shortBreak: 3, longBreak: 10, sessionsBeforeLong: 4 },
    long: { work: 50, shortBreak: 10, longBreak: 30, sessionsBeforeLong: 2 },
}

type PresetKey = keyof typeof PRESETS

export default function PomodoroTimer({ onSessionComplete }: PomodoroTimerProps) {
    const [preset, setPreset] = useState<PresetKey>('classic')
    const [mode, setMode] = useState<'work' | 'shortBreak' | 'longBreak'>('work')
    const [timeLeft, setTimeLeft] = useState(PRESETS[preset].work * 60)
    const [isRunning, setIsRunning] = useState(false)
    const [sessionsCompleted, setSessionsCompleted] = useState(0)
    const [autoStart, setAutoStart] = useState(false)

    const settings = PRESETS[preset]

    const getDuration = useCallback((m: typeof mode) => {
        switch (m) {
            case 'work': return settings.work * 60
            case 'shortBreak': return settings.shortBreak * 60
            case 'longBreak': return settings.longBreak * 60
        }
    }, [settings])

    useEffect(() => {
        let interval: NodeJS.Timeout | null = null

        if (isRunning && timeLeft > 0) {
            interval = setInterval(() => {
                setTimeLeft(prev => prev - 1)
            }, 1000)
        } else if (timeLeft === 0) {
            // Session complete
            if (mode === 'work') {
                const newSessions = sessionsCompleted + 1
                setSessionsCompleted(newSessions)
                onSessionComplete?.('work')

                // Determine next break type
                if (newSessions % settings.sessionsBeforeLong === 0) {
                    setMode('longBreak')
                    setTimeLeft(getDuration('longBreak'))
                } else {
                    setMode('shortBreak')
                    setTimeLeft(getDuration('shortBreak'))
                }

                if (autoStart) setIsRunning(true)
                else setIsRunning(false)
            } else {
                // Break complete
                onSessionComplete?.('break')
                setMode('work')
                setTimeLeft(getDuration('work'))

                if (autoStart) setIsRunning(true)
                else setIsRunning(false)
            }
        }

        return () => {
            if (interval) clearInterval(interval)
        }
    }, [isRunning, timeLeft, mode, sessionsCompleted, settings, autoStart, getDuration, onSessionComplete])

    const toggleTimer = () => setIsRunning(prev => !prev)

    const resetTimer = () => {
        setIsRunning(false)
        setMode('work')
        setTimeLeft(getDuration('work'))
        setSessionsCompleted(0)
    }

    const skipSession = () => {
        setIsRunning(false)
        if (mode === 'work') {
            setMode('shortBreak')
            setTimeLeft(getDuration('shortBreak'))
        } else {
            setMode('work')
            setTimeLeft(getDuration('work'))
        }
    }

    const formatTime = (seconds: number) => {
        const m = Math.floor(seconds / 60)
        const s = seconds % 60
        return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
    }

    const progress = 1 - (timeLeft / getDuration(mode))

    const getModeColor = () => {
        switch (mode) {
            case 'work': return 'from-primary to-secondary'
            case 'shortBreak': return 'from-emerald-400 to-green-500'
            case 'longBreak': return 'from-blue-400 to-indigo-500'
        }
    }

    const getModeLabel = () => {
        switch (mode) {
            case 'work': return 'Focus Time'
            case 'shortBreak': return 'Short Break'
            case 'longBreak': return 'Long Break'
        }
    }

    return (
        <div className="glass rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                    <span className="text-2xl">🍅</span> Pomodoro
                </h3>
                <select
                    value={preset}
                    onChange={(e) => {
                        const newPreset = e.target.value as PresetKey
                        setPreset(newPreset)
                        setTimeLeft(PRESETS[newPreset].work * 60)
                        setMode('work')
                        setIsRunning(false)
                    }}
                    className="bg-surface-light text-zinc-300 text-sm rounded-lg px-3 py-1 border border-white/10"
                >
                    <option value="classic">Classic (25/5)</option>
                    <option value="short">Short (15/3)</option>
                    <option value="long">Long (50/10)</option>
                </select>
            </div>

            {/* Mode indicator */}
            <div className={`text-center py-2 px-4 rounded-lg bg-gradient-to-r ${getModeColor()} mb-4`}>
                <span className="text-sm font-medium text-white">{getModeLabel()}</span>
            </div>

            {/* Timer display */}
            <div className="relative flex items-center justify-center py-8">
                {/* Progress ring */}
                <svg className="absolute w-48 h-48 -rotate-90">
                    <circle
                        cx="96"
                        cy="96"
                        r="88"
                        fill="none"
                        stroke="rgba(255,255,255,0.1)"
                        strokeWidth="8"
                    />
                    <circle
                        cx="96"
                        cy="96"
                        r="88"
                        fill="none"
                        stroke="url(#gradient)"
                        strokeWidth="8"
                        strokeLinecap="round"
                        strokeDasharray={2 * Math.PI * 88}
                        strokeDashoffset={2 * Math.PI * 88 * (1 - progress)}
                        className="transition-all duration-1000"
                    />
                    <defs>
                        <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stopColor="#42D674" />
                            <stop offset="100%" stopColor="#80EF80" />
                        </linearGradient>
                    </defs>
                </svg>

                <div className="text-center z-10">
                    <div className="text-5xl font-bold text-white tabular-nums">
                        {formatTime(timeLeft)}
                    </div>
                    <div className="text-sm text-zinc-400 mt-1">
                        Session {sessionsCompleted + 1}
                    </div>
                </div>
            </div>

            {/* Controls */}
            <div className="flex items-center justify-center gap-3 mb-4">
                <button
                    onClick={resetTimer}
                    className="p-3 rounded-xl bg-surface-light hover:bg-white/10 text-zinc-400 hover:text-white transition"
                    title="Reset"
                >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                </button>

                <button
                    onClick={toggleTimer}
                    className={`p-4 rounded-xl text-white font-medium transition ${isRunning
                            ? 'bg-red-500/80 hover:bg-red-500'
                            : 'gradient-primary hover:opacity-90'
                        }`}
                >
                    {isRunning ? (
                        <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
                        </svg>
                    ) : (
                        <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M8 5v14l11-7z" />
                        </svg>
                    )}
                </button>

                <button
                    onClick={skipSession}
                    className="p-3 rounded-xl bg-surface-light hover:bg-white/10 text-zinc-400 hover:text-white transition"
                    title="Skip"
                >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                    </svg>
                </button>
            </div>

            {/* Auto-start toggle */}
            <div className="flex items-center justify-center gap-2">
                <input
                    type="checkbox"
                    id="autoStart"
                    checked={autoStart}
                    onChange={(e) => setAutoStart(e.target.checked)}
                    className="w-4 h-4 rounded bg-surface-light border-white/20 text-primary focus:ring-primary"
                />
                <label htmlFor="autoStart" className="text-sm text-zinc-400">
                    Auto-start next session
                </label>
            </div>

            {/* Session counter */}
            <div className="mt-4 flex justify-center gap-1">
                {Array.from({ length: settings.sessionsBeforeLong }).map((_, i) => (
                    <div
                        key={i}
                        className={`w-3 h-3 rounded-full transition ${i < (sessionsCompleted % settings.sessionsBeforeLong)
                                ? 'bg-primary'
                                : 'bg-white/10'
                            }`}
                    />
                ))}
            </div>
        </div>
    )
}
