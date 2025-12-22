'use client'

import { useEffect, useState } from 'react'
import { useCopilotContext, Notification } from '@/providers/CopilotProvider'

/**
 * Animated achievement and notification popup component
 * Displays notifications from the AI assistant and system
 */
export default function AchievementPopup() {
    const { appState, clearNotification } = useCopilotContext()
    const [visibleNotifications, setVisibleNotifications] = useState<(Notification & { isExiting?: boolean })[]>([])

    // Sync with app state notifications
    useEffect(() => {
        const newNotifications = appState.notifications.filter(
            n => !visibleNotifications.find(v => v.id === n.id)
        )
        if (newNotifications.length > 0) {
            setVisibleNotifications(prev => [...prev, ...newNotifications])
        }
    }, [appState.notifications])

    const handleDismiss = (id: string) => {
        // Mark as exiting for animation
        setVisibleNotifications(prev =>
            prev.map(n => n.id === id ? { ...n, isExiting: true } : n)
        )

        // Remove after animation
        setTimeout(() => {
            setVisibleNotifications(prev => prev.filter(n => n.id !== id))
            clearNotification(id)
        }, 300)
    }

    if (visibleNotifications.length === 0) {
        return null
    }

    const getNotificationStyles = (type: string) => {
        switch (type) {
            case 'success':
                return {
                    bg: 'bg-green-500/20',
                    border: 'border-green-500/30',
                    icon: 'text-green-400',
                    iconBg: 'bg-green-500/20'
                }
            case 'info':
                return {
                    bg: 'bg-blue-500/20',
                    border: 'border-blue-500/30',
                    icon: 'text-blue-400',
                    iconBg: 'bg-blue-500/20'
                }
            case 'warning':
                return {
                    bg: 'bg-yellow-500/20',
                    border: 'border-yellow-500/30',
                    icon: 'text-yellow-400',
                    iconBg: 'bg-yellow-500/20'
                }
            case 'error':
                return {
                    bg: 'bg-red-500/20',
                    border: 'border-red-500/30',
                    icon: 'text-red-400',
                    iconBg: 'bg-red-500/20'
                }
            case 'achievement':
                return {
                    bg: 'bg-gradient-to-r from-purple-500/20 to-pink-500/20',
                    border: 'border-purple-500/30',
                    icon: 'text-purple-400',
                    iconBg: 'bg-purple-500/20'
                }
            default:
                return {
                    bg: 'bg-surface-light',
                    border: 'border-white/10',
                    icon: 'text-zinc-400',
                    iconBg: 'bg-zinc-500/20'
                }
        }
    }

    const getIcon = (type: string) => {
        switch (type) {
            case 'success':
                return (
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                )
            case 'info':
                return (
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                )
            case 'warning':
                return (
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                )
            case 'error':
                return (
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                )
            case 'achievement':
                return (
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                    </svg>
                )
            default:
                return null
        }
    }

    return (
        <div className="fixed top-4 right-4 z-[100] space-y-3 max-w-sm">
            {visibleNotifications.map(notification => {
                const styles = getNotificationStyles(notification.type)

                return (
                    <div
                        key={notification.id}
                        className={`
                            ${styles.bg} ${styles.border}
                            border rounded-xl p-4 shadow-xl backdrop-blur-sm
                            transform transition-all duration-300
                            ${notification.isExiting
                                ? 'opacity-0 translate-x-full'
                                : 'opacity-100 translate-x-0 animate-slide-in'
                            }
                        `}
                        style={{
                            animation: notification.isExiting ? undefined : 'slideIn 0.3s ease-out'
                        }}
                    >
                        <div className="flex items-start gap-3">
                            {/* Icon */}
                            <div className={`${styles.iconBg} ${styles.icon} w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0`}>
                                {getIcon(notification.type)}
                            </div>

                            {/* Content */}
                            <div className="flex-1 min-w-0">
                                <h4 className="font-semibold text-white text-sm">
                                    {notification.title}
                                </h4>
                                <p className="text-zinc-400 text-sm mt-0.5 line-clamp-2">
                                    {notification.message}
                                </p>
                            </div>

                            {/* Dismiss button */}
                            <button
                                onClick={() => handleDismiss(notification.id)}
                                className="text-zinc-500 hover:text-white transition-colors flex-shrink-0"
                            >
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>

                        {/* Achievement special effects */}
                        {notification.type === 'achievement' && (
                            <>
                                {/* Sparkle effects */}
                                <div className="absolute -top-1 -left-1">
                                    <span className="text-lg animate-ping">*</span>
                                </div>
                                <div className="absolute -top-1 -right-1">
                                    <span className="text-lg animate-ping" style={{ animationDelay: '0.2s' }}>*</span>
                                </div>
                                <div className="absolute -bottom-1 left-1/2">
                                    <span className="text-lg animate-ping" style={{ animationDelay: '0.4s' }}>*</span>
                                </div>

                                {/* Progress bar animation */}
                                <div className="mt-3 h-1 bg-purple-900/30 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full"
                                        style={{
                                            animation: 'fillBar 2s ease-out forwards'
                                        }}
                                    />
                                </div>
                            </>
                        )}

                        {/* Auto-dismiss progress bar for non-achievements */}
                        {notification.type !== 'achievement' && (
                            <div className="mt-3 h-0.5 bg-white/10 rounded-full overflow-hidden">
                                <div
                                    className={`h-full ${styles.icon.replace('text-', 'bg-')} rounded-full`}
                                    style={{
                                        animation: 'shrinkBar 5s linear forwards'
                                    }}
                                />
                            </div>
                        )}
                    </div>
                )
            })}

            {/* Animation keyframes */}
            <style jsx>{`
                @keyframes slideIn {
                    from {
                        opacity: 0;
                        transform: translateX(100%);
                    }
                    to {
                        opacity: 1;
                        transform: translateX(0);
                    }
                }
                @keyframes fillBar {
                    from {
                        width: 0%;
                    }
                    to {
                        width: 100%;
                    }
                }
                @keyframes shrinkBar {
                    from {
                        width: 100%;
                    }
                    to {
                        width: 0%;
                    }
                }
            `}</style>
        </div>
    )
}

/**
 * Standalone achievement component for special celebrations
 */
export function AchievementCelebration({
    title,
    description,
    icon = 'trophy',
    points,
    onClose
}: {
    title: string
    description: string
    icon?: string
    points?: number
    onClose: () => void
}) {
    const [isVisible, setIsVisible] = useState(false)

    useEffect(() => {
        setIsVisible(true)
        // Auto-close after 5 seconds
        const timer = setTimeout(() => {
            setIsVisible(false)
            setTimeout(onClose, 300)
        }, 5000)
        return () => clearTimeout(timer)
    }, [onClose])

    return (
        <>
            {/* Backdrop with confetti effect */}
            <div
                className={`fixed inset-0 bg-black/60 backdrop-blur-sm z-[100] transition-opacity duration-300 ${isVisible ? 'opacity-100' : 'opacity-0'
                    }`}
                onClick={() => {
                    setIsVisible(false)
                    setTimeout(onClose, 300)
                }}
            />

            {/* Achievement card */}
            <div
                className={`
                    fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2
                    w-full max-w-sm z-[100]
                    transition-all duration-500
                    ${isVisible ? 'opacity-100 scale-100' : 'opacity-0 scale-75'}
                `}
            >
                <div className="glass rounded-2xl p-8 text-center relative overflow-hidden">
                    {/* Gradient background */}
                    <div className="absolute inset-0 bg-gradient-to-br from-purple-500/20 via-pink-500/20 to-orange-500/20" />

                    {/* Content */}
                    <div className="relative">
                        {/* Trophy icon with glow */}
                        <div className="w-20 h-20 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-yellow-400 to-orange-500 flex items-center justify-center shadow-lg shadow-yellow-500/30 animate-bounce-slow">
                            <span className="text-4xl">{icon}</span>
                        </div>

                        <h2 className="text-2xl font-bold text-white mb-2">
                            {title}
                        </h2>

                        <p className="text-zinc-400 mb-4">
                            {description}
                        </p>

                        {points && (
                            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-yellow-500/20 text-yellow-400">
                                <span className="text-lg">+</span>
                                <span className="font-bold text-lg">{points}</span>
                                <span className="text-sm">points</span>
                            </div>
                        )}

                        <button
                            onClick={() => {
                                setIsVisible(false)
                                setTimeout(onClose, 300)
                            }}
                            className="block w-full mt-6 py-3 rounded-xl gradient-primary text-white font-medium hover:opacity-90 transition"
                        >
                            Awesome!
                        </button>
                    </div>

                    {/* Decorative particles */}
                    <div className="absolute top-4 left-4 w-2 h-2 rounded-full bg-purple-400 animate-ping" />
                    <div className="absolute top-8 right-6 w-2 h-2 rounded-full bg-pink-400 animate-ping" style={{ animationDelay: '0.2s' }} />
                    <div className="absolute bottom-12 left-8 w-2 h-2 rounded-full bg-orange-400 animate-ping" style={{ animationDelay: '0.4s' }} />
                    <div className="absolute bottom-8 right-4 w-2 h-2 rounded-full bg-yellow-400 animate-ping" style={{ animationDelay: '0.6s' }} />
                </div>
            </div>
        </>
    )
}
