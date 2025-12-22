'use client'

import { useState, useRef, useEffect } from 'react'

interface Message {
    id: string
    role: 'user' | 'assistant' | 'system'
    content: string
    tool_calls?: { tool: string; result: any }[]
    timestamp: Date
}

export default function AICommandCenter() {
    const [messages, setMessages] = useState<Message[]>([
        {
            id: '1',
            role: 'assistant',
            content: "Hello! I'm your Engineering OS assistant. I can help you manage your schedule, track revisions, and optimize your study time. Try saying:\n\n• \"What should I revise today?\"\n• \"I finished PHYS 102 Chapter 3\"\n• \"Add rule: No studying after 21:00\"",
            timestamp: new Date()
        }
    ])
    const [input, setInput] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const messagesEndRef = useRef<HTMLDivElement>(null)
    const inputRef = useRef<HTMLInputElement>(null)

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    const sendMessage = async () => {
        if (!input.trim() || isLoading) return

        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: input.trim(),
            timestamp: new Date()
        }

        setMessages(prev => [...prev, userMessage])
        setInput('')
        setIsLoading(true)

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: userMessage.content })
            })

            const data = await response.json()

            const assistantMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: data.response || "I processed your request.",
                tool_calls: data.tool_calls,
                timestamp: new Date()
            }

            setMessages(prev => [...prev, assistantMessage])
        } catch (error) {
            const errorMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: "⚠️ Connection error. Make sure the backend is running on port 8000 and copilot-api on port 4141.",
                timestamp: new Date()
            }
            setMessages(prev => [...prev, errorMessage])
        } finally {
            setIsLoading(false)
        }
    }

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            sendMessage()
        }
    }

    const quickActions = [
        { label: "📊 Morning briefing", message: "Give me my morning briefing" },
        { label: "📚 What to revise?", message: "What should I revise today?" },
        { label: "⏰ Find free time", message: "Analyze my schedule for deep work gaps" },
    ]

    return (
        <div className="glass rounded-2xl flex flex-col h-[600px]">
            {/* Header */}
            <div className="px-4 py-3 border-b border-white/10">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg gradient-primary flex items-center justify-center">
                        <span className="text-lg">🤖</span>
                    </div>
                    <div>
                        <h3 className="font-semibold text-white">AI Command Center</h3>
                        <p className="text-xs text-zinc-400">Powered by GitHub Copilot</p>
                    </div>
                </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.map(message => (
                    <div
                        key={message.id}
                        className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                        <div
                            className={`max-w-[85%] rounded-2xl px-4 py-3 ${message.role === 'user'
                                    ? 'bg-primary text-white rounded-br-md'
                                    : 'bg-surface-light text-zinc-100 rounded-bl-md'
                                }`}
                        >
                            <p className="text-sm whitespace-pre-wrap">{message.content}</p>

                            {/* Tool calls display */}
                            {message.tool_calls && message.tool_calls.length > 0 && (
                                <div className="mt-3 pt-3 border-t border-white/10">
                                    <p className="text-xs text-zinc-400 mb-2">Actions performed:</p>
                                    {message.tool_calls.map((tc, i) => (
                                        <div key={i} className="text-xs bg-black/20 rounded px-2 py-1 mb-1">
                                            <span className="text-primary">⚡ {tc.tool}</span>
                                            {tc.result?.success && (
                                                <span className="text-green-400 ml-2">✓</span>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}

                            <p className="text-xs text-zinc-500 mt-2">
                                {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </p>
                        </div>
                    </div>
                ))}

                {/* Typing indicator */}
                {isLoading && (
                    <div className="flex justify-start">
                        <div className="bg-surface-light rounded-2xl rounded-bl-md px-4 py-3">
                            <div className="flex gap-1">
                                <span className="w-2 h-2 rounded-full bg-zinc-400 typing-dot"></span>
                                <span className="w-2 h-2 rounded-full bg-zinc-400 typing-dot"></span>
                                <span className="w-2 h-2 rounded-full bg-zinc-400 typing-dot"></span>
                            </div>
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Quick Actions */}
            <div className="px-4 py-2 border-t border-white/10">
                <div className="flex gap-2 overflow-x-auto pb-2">
                    {quickActions.map((action, i) => (
                        <button
                            key={i}
                            onClick={() => {
                                setInput(action.message)
                                inputRef.current?.focus()
                            }}
                            className="flex-shrink-0 text-xs px-3 py-1.5 rounded-full bg-surface-light hover:bg-primary/30 text-zinc-300 hover:text-white transition"
                        >
                            {action.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Input */}
            <div className="p-4 border-t border-white/10">
                <div className="flex gap-2">
                    <input
                        ref={inputRef}
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Type a command..."
                        className="flex-1 bg-surface-light rounded-xl px-4 py-3 text-white placeholder-zinc-500 outline-none focus:ring-2 focus:ring-primary/50"
                        disabled={isLoading}
                    />
                    <button
                        onClick={sendMessage}
                        disabled={isLoading || !input.trim()}
                        className="px-4 py-3 rounded-xl gradient-primary text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-90 transition"
                    >
                        <span className="text-lg">↑</span>
                    </button>
                </div>
            </div>
        </div>
    )
}
