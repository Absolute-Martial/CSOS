'use client'

import { useCopilotAction } from '@copilotkit/react-core'
import { useCopilotContext, ScheduleChange } from '@/providers/CopilotProvider'

/**
 * Hook that registers frontend tools for CopilotKit
 * These tools allow the AI to interact with the UI
 */
export function useCopilotTools() {
    const {
        setActiveTab,
        setHighlightedTaskId,
        addNotification,
        setFocusMode,
        showScheduleConfirmation,
        appState
    } = useCopilotContext()

    // Navigate to a specific tab
    useCopilotAction({
        name: 'navigateToTab',
        description: 'Navigate to a specific tab in the application (today, timeline, tasks, labs, analytics, goals)',
        parameters: [
            {
                name: 'tab',
                type: 'string',
                description: 'The tab to navigate to',
                required: true,
                enum: ['today', 'timeline', 'tasks', 'labs', 'analytics', 'goals']
            }
        ],
        handler: async ({ tab }) => {
            setActiveTab(tab)
            return {
                success: true,
                message: `Navigated to ${tab} tab`
            }
        }
    })

    // Highlight a specific task
    useCopilotAction({
        name: 'highlightTask',
        description: 'Highlight a specific task in the UI to draw user attention',
        parameters: [
            {
                name: 'taskId',
                type: 'number',
                description: 'The ID of the task to highlight',
                required: true
            },
            {
                name: 'duration',
                type: 'number',
                description: 'How long to highlight in milliseconds (default 3000)',
                required: false
            }
        ],
        handler: async ({ taskId, duration = 3000 }) => {
            setHighlightedTaskId(taskId)

            // Auto-clear highlight after duration
            setTimeout(() => {
                setHighlightedTaskId(null)
            }, duration)

            // Navigate to tasks tab if not there
            if (appState.activeTab !== 'tasks' && appState.activeTab !== 'today') {
                setActiveTab('tasks')
            }

            return {
                success: true,
                message: `Highlighted task ${taskId}`
            }
        }
    })

    // Show notification
    useCopilotAction({
        name: 'showNotification',
        description: 'Show a notification to the user',
        parameters: [
            {
                name: 'type',
                type: 'string',
                description: 'The type of notification',
                required: true,
                enum: ['success', 'info', 'warning', 'error']
            },
            {
                name: 'title',
                type: 'string',
                description: 'The notification title',
                required: true
            },
            {
                name: 'message',
                type: 'string',
                description: 'The notification message',
                required: true
            }
        ],
        handler: async ({ type, title, message }) => {
            addNotification({
                type: type as 'success' | 'info' | 'warning' | 'error',
                title,
                message
            })
            return {
                success: true,
                message: 'Notification shown'
            }
        }
    })

    // Show confirmation dialog for schedule changes
    useCopilotAction({
        name: 'showConfirmation',
        description: 'Show a confirmation dialog for schedule changes before applying them',
        parameters: [
            {
                name: 'changes',
                type: 'object[]',
                description: 'Array of schedule changes to confirm',
                required: true
            }
        ],
        handler: async ({ changes }) => {
            const confirmed = await showScheduleConfirmation(changes as ScheduleChange[])
            return {
                success: true,
                confirmed,
                message: confirmed ? 'User confirmed changes' : 'User cancelled changes'
            }
        }
    })

    // Start focus mode
    useCopilotAction({
        name: 'startFocusMode',
        description: 'Enable focus mode to minimize distractions during study sessions',
        parameters: [
            {
                name: 'duration',
                type: 'number',
                description: 'Duration in minutes (optional, for auto-disable)',
                required: false
            }
        ],
        handler: async ({ duration }) => {
            setFocusMode(true)

            addNotification({
                type: 'info',
                title: 'Focus Mode Enabled',
                message: duration
                    ? `Focus mode will auto-disable after ${duration} minutes`
                    : 'Focus mode is now active. Stay concentrated!'
            })

            // Auto-disable after duration if specified
            if (duration) {
                setTimeout(() => {
                    setFocusMode(false)
                    addNotification({
                        type: 'success',
                        title: 'Focus Session Complete',
                        message: `Great job! You completed a ${duration} minute focus session.`
                    })
                }, duration * 60 * 1000)
            }

            return {
                success: true,
                message: `Focus mode enabled${duration ? ` for ${duration} minutes` : ''}`
            }
        }
    })

    // Exit focus mode
    useCopilotAction({
        name: 'exitFocusMode',
        description: 'Disable focus mode and return to normal view',
        parameters: [],
        handler: async () => {
            setFocusMode(false)
            return {
                success: true,
                message: 'Focus mode disabled'
            }
        }
    })

    // Show achievement popup
    useCopilotAction({
        name: 'showAchievement',
        description: 'Show an achievement notification to celebrate user progress',
        parameters: [
            {
                name: 'title',
                type: 'string',
                description: 'Achievement title',
                required: true
            },
            {
                name: 'description',
                type: 'string',
                description: 'Achievement description',
                required: true
            },
            {
                name: 'icon',
                type: 'string',
                description: 'Emoji icon for the achievement',
                required: false
            },
            {
                name: 'points',
                type: 'number',
                description: 'Points earned (optional)',
                required: false
            }
        ],
        handler: async ({ title, description, icon = 'trophy', points }) => {
            addNotification({
                type: 'achievement',
                title: `${icon} ${title}`,
                message: points ? `${description} (+${points} points)` : description
            })
            return {
                success: true,
                message: 'Achievement shown'
            }
        }
    })

    // Scroll to specific section
    useCopilotAction({
        name: 'scrollToSection',
        description: 'Scroll to a specific section on the current page',
        parameters: [
            {
                name: 'sectionId',
                type: 'string',
                description: 'The ID of the section to scroll to',
                required: true
            }
        ],
        handler: async ({ sectionId }) => {
            const element = document.getElementById(sectionId)
            if (element) {
                element.scrollIntoView({ behavior: 'smooth', block: 'start' })
                return {
                    success: true,
                    message: `Scrolled to ${sectionId}`
                }
            }
            return {
                success: false,
                message: `Section ${sectionId} not found`
            }
        }
    })

    // Open external resource
    useCopilotAction({
        name: 'openResource',
        description: 'Open an external resource in a new tab (for study materials, documentation, etc.)',
        parameters: [
            {
                name: 'url',
                type: 'string',
                description: 'The URL to open',
                required: true
            },
            {
                name: 'title',
                type: 'string',
                description: 'Description of the resource',
                required: false
            }
        ],
        handler: async ({ url, title }) => {
            window.open(url, '_blank', 'noopener,noreferrer')

            if (title) {
                addNotification({
                    type: 'info',
                    title: 'Resource Opened',
                    message: `Opening: ${title}`
                })
            }

            return {
                success: true,
                message: `Opened ${title || url}`
            }
        }
    })

    // Play notification sound
    useCopilotAction({
        name: 'playSound',
        description: 'Play a notification sound (for timer alerts, reminders, etc.)',
        parameters: [
            {
                name: 'type',
                type: 'string',
                description: 'The type of sound to play',
                required: true,
                enum: ['notification', 'success', 'warning', 'timer']
            }
        ],
        handler: async ({ type }) => {
            // Create audio context for system sounds
            try {
                const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
                const oscillator = audioContext.createOscillator()
                const gainNode = audioContext.createGain()

                oscillator.connect(gainNode)
                gainNode.connect(audioContext.destination)

                // Different frequencies for different sound types
                const frequencies: Record<string, number[]> = {
                    notification: [523, 659],  // C5, E5
                    success: [523, 659, 784],  // C5, E5, G5 (major chord)
                    warning: [440, 349],       // A4, F4
                    timer: [880, 880, 880]     // High A
                }

                const freqs = frequencies[type] || frequencies.notification

                for (let i = 0; i < freqs.length; i++) {
                    setTimeout(() => {
                        oscillator.frequency.setValueAtTime(freqs[i], audioContext.currentTime)
                        oscillator.type = 'sine'
                        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime)
                        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3)
                    }, i * 200)
                }

                oscillator.start()
                setTimeout(() => oscillator.stop(), freqs.length * 200 + 300)

                return {
                    success: true,
                    message: `Played ${type} sound`
                }
            } catch (error) {
                return {
                    success: false,
                    message: 'Could not play sound'
                }
            }
        }
    })

    // Copy text to clipboard
    useCopilotAction({
        name: 'copyToClipboard',
        description: 'Copy text to the user\'s clipboard',
        parameters: [
            {
                name: 'text',
                type: 'string',
                description: 'The text to copy',
                required: true
            },
            {
                name: 'showNotification',
                type: 'boolean',
                description: 'Whether to show a notification after copying',
                required: false
            }
        ],
        handler: async ({ text, showNotification: notify = true }) => {
            try {
                await navigator.clipboard.writeText(text)

                if (notify) {
                    addNotification({
                        type: 'success',
                        title: 'Copied',
                        message: 'Text copied to clipboard'
                    })
                }

                return {
                    success: true,
                    message: 'Text copied to clipboard'
                }
            } catch (error) {
                return {
                    success: false,
                    message: 'Failed to copy to clipboard'
                }
            }
        }
    })
}
