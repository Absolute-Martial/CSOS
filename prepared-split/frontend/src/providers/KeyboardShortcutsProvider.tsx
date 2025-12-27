'use client'

import { ReactNode } from 'react'
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts'

interface KeyboardShortcutsProviderProps {
    children: ReactNode
}

export default function KeyboardShortcutsProvider({ children }: KeyboardShortcutsProviderProps) {
    // Initialize keyboard shortcuts
    useKeyboardShortcuts()

    return <>{children}</>
}
