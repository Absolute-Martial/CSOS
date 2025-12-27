'use client'

import { useState, useEffect } from 'react'
import { SHORTCUT_LIST } from '@/hooks/useKeyboardShortcuts'

export default function ShortcutsHelp() {
    const [isOpen, setIsOpen] = useState(false)

    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            // Ctrl+? or Ctrl+Shift+/ to toggle help
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === '/') {
                e.preventDefault()
                setIsOpen(prev => !prev)
            }
        }

        window.addEventListener('keydown', handleKeyDown)
        return () => window.removeEventListener('keydown', handleKeyDown)
    }, [])

    if (!isOpen) return null

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
            <div className="glass rounded-2xl p-6 max-w-md w-full mx-4 animate-in fade-in zoom-in duration-200">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-bold text-white">Keyboard Shortcuts</h2>
                    <button
                        onClick={() => setIsOpen(false)}
                        className="text-zinc-400 hover:text-white transition"
                    >
                        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                <div className="space-y-3">
                    {SHORTCUT_LIST.map((shortcut, index) => (
                        <div key={index} className="flex items-center justify-between py-2 border-b border-white/10 last:border-0">
                            <span className="text-zinc-300">{shortcut.description}</span>
                            <div className="flex gap-1">
                                {shortcut.keys.map((key, i) => (
                                    <kbd
                                        key={i}
                                        className="px-2 py-1 text-xs font-mono bg-surface-light rounded border border-white/20 text-zinc-200"
                                    >
                                        {key}
                                    </kbd>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>

                <p className="mt-4 text-xs text-zinc-500 text-center">
                    Press <kbd className="px-1 py-0.5 bg-surface-light rounded text-zinc-300">Ctrl+Shift+/</kbd> to toggle this help
                </p>
            </div>
        </div>
    )
}
