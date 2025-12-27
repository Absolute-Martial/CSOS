'use client'

import { useState, useEffect } from 'react'
import { requestNotificationPermission, subscribeToPush } from './ServiceWorkerRegistration'

export default function NotificationSettings() {
    const [permission, setPermission] = useState<NotificationPermission>('default')
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        if (typeof window !== 'undefined' && 'Notification' in window) {
            setPermission(Notification.permission)
        }
    }, [])

    const handleEnableNotifications = async () => {
        setLoading(true)
        try {
            const granted = await requestNotificationPermission()
            if (granted) {
                setPermission('granted')
                await subscribeToPush()
            } else {
                setPermission('denied')
            }
        } finally {
            setLoading(false)
        }
    }

    const handleTestNotification = () => {
        if (permission === 'granted') {
            new Notification('Engineering OS', {
                body: 'Notifications are working! 🎉',
                icon: '/icons/icon-192.png',
            })
        }
    }

    return (
        <div className="glass rounded-2xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <span className="text-xl">🔔</span> Notifications
            </h3>

            <div className="space-y-4">
                {/* Permission status */}
                <div className="flex items-center justify-between">
                    <span className="text-zinc-400">Status</span>
                    <span className={`text-sm px-2 py-1 rounded ${permission === 'granted'
                            ? 'bg-green-500/20 text-green-400'
                            : permission === 'denied'
                                ? 'bg-red-500/20 text-red-400'
                                : 'bg-zinc-500/20 text-zinc-400'
                        }`}>
                        {permission === 'granted' ? 'Enabled' : permission === 'denied' ? 'Blocked' : 'Not Set'}
                    </span>
                </div>

                {/* Enable button */}
                {permission !== 'granted' && (
                    <button
                        onClick={handleEnableNotifications}
                        disabled={loading || permission === 'denied'}
                        className="w-full py-2 px-4 rounded-lg gradient-primary text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-90 transition"
                    >
                        {loading ? 'Enabling...' : permission === 'denied' ? 'Blocked by Browser' : 'Enable Notifications'}
                    </button>
                )}

                {permission === 'denied' && (
                    <p className="text-xs text-zinc-500">
                        Notifications are blocked. Please enable them in your browser settings.
                    </p>
                )}

                {/* Test button */}
                {permission === 'granted' && (
                    <button
                        onClick={handleTestNotification}
                        className="w-full py-2 px-4 rounded-lg bg-surface-light text-zinc-300 hover:bg-white/10 transition"
                    >
                        Send Test Notification
                    </button>
                )}

                {/* Notification preferences */}
                {permission === 'granted' && (
                    <div className="space-y-3 pt-4 border-t border-white/10">
                        <h4 className="text-sm font-medium text-zinc-400">Notify me about:</h4>

                        <label className="flex items-center justify-between cursor-pointer">
                            <span className="text-sm text-zinc-300">Daily summaries</span>
                            <input type="checkbox" defaultChecked className="w-4 h-4 rounded bg-surface-light" />
                        </label>

                        <label className="flex items-center justify-between cursor-pointer">
                            <span className="text-sm text-zinc-300">Upcoming deadlines</span>
                            <input type="checkbox" defaultChecked className="w-4 h-4 rounded bg-surface-light" />
                        </label>

                        <label className="flex items-center justify-between cursor-pointer">
                            <span className="text-sm text-zinc-300">Study reminders</span>
                            <input type="checkbox" defaultChecked className="w-4 h-4 rounded bg-surface-light" />
                        </label>

                        <label className="flex items-center justify-between cursor-pointer">
                            <span className="text-sm text-zinc-300">Spaced repetition reviews</span>
                            <input type="checkbox" defaultChecked className="w-4 h-4 rounded bg-surface-light" />
                        </label>
                    </div>
                )}
            </div>
        </div>
    )
}
