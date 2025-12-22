'use client'

import { useEffect, useState } from 'react'

interface HealthStatus {
    status: string
    version: string
    database: string
    copilot_api: string
}

export default function SystemBadge() {
    const [health, setHealth] = useState<HealthStatus | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        checkHealth()
        // Poll every 30 seconds
        const interval = setInterval(checkHealth, 30000)
        return () => clearInterval(interval)
    }, [])

    const checkHealth = async () => {
        try {
            const res = await fetch('/api/health', { cache: 'no-store' })
            if (res.ok) {
                setHealth(await res.json())
            } else {
                setHealth(null)
            }
        } catch {
            setHealth(null)
        } finally {
            setLoading(false)
        }
    }

    const getStatusColor = (status: string | undefined) => {
        switch (status) {
            case 'connected':
            case 'healthy':
                return 'bg-green-500'
            case 'disconnected':
            case 'error':
                return 'bg-red-500'
            default:
                return 'bg-yellow-500'
        }
    }

    const isHealthy = health?.status === 'healthy' && health?.database === 'connected'

    return (
        <footer className="glass border-t border-white/10 px-6 py-3">
            <div className="max-w-7xl mx-auto flex items-center justify-between">
                {/* Version */}
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                        <span className="text-xs text-zinc-500">Version</span>
                        <span className="text-sm font-mono text-primary">
                            v{health?.version || '1.0.1'}
                        </span>
                    </div>

                    <div className="w-px h-4 bg-zinc-700"></div>

                    <div className="text-xs text-zinc-500">
                        Personal Engineering OS
                    </div>
                </div>

                {/* Status Indicators */}
                <div className="flex items-center gap-4">
                    {loading ? (
                        <div className="flex items-center gap-2">
                            <div className="w-2 h-2 rounded-full bg-zinc-500 animate-pulse"></div>
                            <span className="text-xs text-zinc-500">Checking...</span>
                        </div>
                    ) : (
                        <>
                            {/* API Status */}
                            <div className="flex items-center gap-2">
                                <div className={`w-2 h-2 rounded-full ${getStatusColor(health?.status)}`}></div>
                                <span className="text-xs text-zinc-400">
                                    API: {health?.status || 'offline'}
                                </span>
                            </div>

                            {/* Database Status */}
                            <div className="flex items-center gap-2">
                                <div className={`w-2 h-2 rounded-full ${getStatusColor(health?.database)}`}></div>
                                <span className="text-xs text-zinc-400">
                                    DB: {health?.database || 'offline'}
                                </span>
                            </div>

                            {/* Copilot API Status */}
                            <div className="flex items-center gap-2">
                                <div className={`w-2 h-2 rounded-full ${getStatusColor(health?.copilot_api)}`}></div>
                                <span className="text-xs text-zinc-400">
                                    AI: {health?.copilot_api || 'offline'}
                                </span>
                            </div>
                        </>
                    )}

                    {/* Overall Status Badge */}
                    <div className={`px-3 py-1 rounded-full text-xs font-medium ${isHealthy
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-red-500/20 text-red-400'
                        }`}>
                        {isHealthy ? '● Operational' : '● Degraded'}
                    </div>
                </div>
            </div>
        </footer>
    )
}
