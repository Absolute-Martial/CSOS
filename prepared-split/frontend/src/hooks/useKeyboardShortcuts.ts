'use client'

import { useEffect, useCallback } from 'react'
import { useCopilotContext } from '@/providers/CopilotProvider'

interface ShortcutConfig {
    key: string
    ctrl?: boolean
    alt?: boolean
    shift?: boolean
    action: () => void
    description: string
}

export function useKeyboardShortcuts() {
    const { setActiveTab, appState } = useCopilotContext()

    const shortcuts: ShortcutConfig[] = [
        // Tab navigation (1-5)
        { key: '1', action: () => setActiveTab('today'), description: 'Go to Today' },
        { key: '2', action: () => setActiveTab('schedule'), description: 'Go to Schedule' },
        { key: '3', action: () => setActiveTab('analytics'), description: 'Go to Analytics' },
        { key: '4', action: () => setActiveTab('goals'), description: 'Go to Goals' },
        { key: '5', action: () => setActiveTab('settings'), description: 'Go to Settings' },

        // Timer control
        {
            key: 't',
            ctrl: true,
            action: () => {
                // Toggle timer - dispatch custom event
                window.dispatchEvent(new CustomEvent('toggle-timer'))
            },
            description: 'Toggle Timer'
        },

        // New task
        {
            key: 'n',
            ctrl: true,
            action: () => {
                window.dispatchEvent(new CustomEvent('new-task'))
            },
            description: 'New Task'
        },

        // Focus chat
        {
            key: '/',
            ctrl: true,
            action: () => {
                const chatInput = document.querySelector('input[placeholder*="Ask"]') as HTMLInputElement
                chatInput?.focus()
            },
            description: 'Focus Chat'
        },

        // Escape to close modals
        {
            key: 'Escape',
            action: () => {
                window.dispatchEvent(new CustomEvent('close-modal'))
            },
            description: 'Close Modal'
        }
    ]

    const handleKeyDown = useCallback((event: KeyboardEvent) => {
        // Don't trigger shortcuts when typing in inputs
        const target = event.target as HTMLElement
        if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
            // Only allow Escape in inputs
            if (event.key !== 'Escape') return
        }

        for (const shortcut of shortcuts) {
            const ctrlMatch = shortcut.ctrl ? (event.ctrlKey || event.metaKey) : !event.ctrlKey
            const altMatch = shortcut.alt ? event.altKey : !event.altKey
            const shiftMatch = shortcut.shift ? event.shiftKey : !event.shiftKey

            if (
                event.key.toLowerCase() === shortcut.key.toLowerCase() &&
                ctrlMatch &&
                altMatch &&
                shiftMatch
            ) {
                event.preventDefault()
                shortcut.action()
                return
            }
        }
    }, [shortcuts])

    useEffect(() => {
        window.addEventListener('keydown', handleKeyDown)
        return () => window.removeEventListener('keydown', handleKeyDown)
    }, [handleKeyDown])

    return { shortcuts }
}

// Export shortcut list for help display
export const SHORTCUT_LIST = [
    { keys: ['1', '2', '3', '4', '5'], description: 'Switch tabs' },
    { keys: ['Ctrl', 'T'], description: 'Toggle timer' },
    { keys: ['Ctrl', 'N'], description: 'New task' },
    { keys: ['Ctrl', '/'], description: 'Focus chat' },
    { keys: ['Esc'], description: 'Close modal' },
]
