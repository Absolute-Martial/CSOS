'use client'

import { useState, useEffect, useRef } from 'react'

interface FloatingTimerProps {
    isRunning: boolean
    elapsedSeconds: number
    subjectName?: string
    color?: string
    onToggle?: () => void
    onStop?: () => void
}

export default function FloatingTimer({
    isRunning,
    elapsedSeconds,
    subjectName,
    color = '#42D674',
    onToggle,
    onStop,
}: FloatingTimerProps) {
    const [isMinimized, setIsMinimized] = useState(false)
    const [position, setPosition] = useState({ x: 20, y: 20 })
    const [isDragging, setIsDragging] = useState(false)
    const dragRef = useRef<{ startX: number; startY: number; posX: number; posY: number } | null>(null)
    const containerRef = useRef<HTMLDivElement>(null)

    const formatTime = (seconds: number) => {
        const h = Math.floor(seconds / 3600)
        const m = Math.floor((seconds % 3600) / 60)
        const s = seconds % 60
        if (h > 0) {
            return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
        }
        return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
    }

    const handleMouseDown = (e: React.MouseEvent) => {
        if ((e.target as HTMLElement).tagName === 'BUTTON') return
        setIsDragging(true)
        dragRef.current = {
            startX: e.clientX,
            startY: e.clientY,
            posX: position.x,
            posY: position.y,
        }
    }

    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            if (!isDragging || !dragRef.current) return

            const deltaX = e.clientX - dragRef.current.startX
            const deltaY = e.clientY - dragRef.current.startY

            const newX = Math.max(0, Math.min(window.innerWidth - 200, dragRef.current.posX + deltaX))
            const newY = Math.max(0, Math.min(window.innerHeight - 80, dragRef.current.posY + deltaY))

            setPosition({ x: newX, y: newY })
        }

        const handleMouseUp = () => {
            setIsDragging(false)
            dragRef.current = null
        }

        if (isDragging) {
            window.addEventListener('mousemove', handleMouseMove)
            window.addEventListener('mouseup', handleMouseUp)
        }

        return () => {
            window.removeEventListener('mousemove', handleMouseMove)
            window.removeEventListener('mouseup', handleMouseUp)
        }
    }, [isDragging])

    // Don't render if timer is not running
    if (!isRunning && elapsedSeconds === 0) return null

    return (
        <div
            ref={containerRef}
            className={`fixed z-50 select-none transition-all duration-200 ${isDragging ? 'cursor-grabbing' : 'cursor-grab'}`}
            style={{
                left: position.x,
                top: position.y,
            }}
            onMouseDown={handleMouseDown}
        >
            {isMinimized ? (
                // Minimized view - just a small pill
                <div
                    className="flex items-center gap-2 px-3 py-2 rounded-full backdrop-blur-lg border border-white/20"
                    style={{ backgroundColor: `${color}20` }}
                    onClick={() => setIsMinimized(false)}
                >
                    <div
                        className={`w-2 h-2 rounded-full ${isRunning ? 'animate-pulse' : ''}`}
                        style={{ backgroundColor: color }}
                    />
                    <span className="text-sm font-mono text-white">{formatTime(elapsedSeconds)}</span>
                </div>
            ) : (
                // Expanded view
                <div
                    className="backdrop-blur-lg rounded-2xl border border-white/20 p-3 shadow-2xl"
                    style={{ backgroundColor: 'rgba(10, 10, 15, 0.9)' }}
                >
                    <div className="flex items-center gap-3 mb-2">
                        <div
                            className={`w-3 h-3 rounded-full ${isRunning ? 'animate-pulse' : ''}`}
                            style={{ backgroundColor: color }}
                        />
                        <span className="text-xs text-zinc-400 truncate max-w-[100px]">
                            {subjectName || 'Study Session'}
                        </span>
                        <button
                            onClick={() => setIsMinimized(true)}
                            className="ml-auto p-1 text-zinc-500 hover:text-white transition"
                        >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                            </svg>
                        </button>
                    </div>

                    <div className="text-2xl font-bold font-mono text-white text-center mb-2">
                        {formatTime(elapsedSeconds)}
                    </div>

                    <div className="flex items-center justify-center gap-2">
                        <button
                            onClick={onToggle}
                            className={`p-2 rounded-lg transition ${isRunning
                                    ? 'bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500/30'
                                    : 'bg-primary/20 text-primary hover:bg-primary/30'
                                }`}
                        >
                            {isRunning ? (
                                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                                    <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
                                </svg>
                            ) : (
                                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                                    <path d="M8 5v14l11-7z" />
                                </svg>
                            )}
                        </button>
                        <button
                            onClick={onStop}
                            className="p-2 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 transition"
                        >
                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M6 6h12v12H6z" />
                            </svg>
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}
