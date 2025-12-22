'use client'

import { useState, useRef, useEffect } from 'react'
import { useCopilotChat, useCopilotAction, useCopilotReadable } from '@copilotkit/react-core'
import { useCopilotContext } from '@/providers/CopilotProvider'
import { COPILOT_CONFIG } from '@/lib/copilot-config'
import { useCopilotTools } from '@/hooks/useCopilotTools'
import { useCopilotContextSync } from '@/hooks/useCopilotContext'

interface Message {
    id: string
    role: 'user' | 'assistant' | 'system'
    content: string
    toolCalls?: { tool: string; result: any }[]
    isStreaming?: boolean
}

export default function AIAssistant() {
    const [messages, setMessages] = useState<Message[]>([
        {
            id: '1',
            role: 'assistant',
            content: COPILOT_CONFIG.chat.initialMessage,
        }
    ])
    const [input, setInput] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const messagesEndRef = useRef<HTMLDivElement>(null)
    const inputRef = useRef<HTMLInputElement>(null)

    const { appState, addNotification, focusMode } = useCopilotContext()

    // Register frontend tools
    useCopilotTools()

    // Sync app state with CopilotKit
    useCopilotContextSync()

    // CopilotKit chat hook
    const { sendMessage: copilotSendMessage, isLoading: copilotLoading } = useCopilotChat({
        onMessage: (message) => {
            if (message.role === 'assistant') {
                const assistantMessage: Message = {
                    id: `msg-${Date.now()}`,
                    role: 'assistant',
                    content: message.content || '',
                }
                setMessages(prev => [...prev, assistantMessage])
            }
        }
    })

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    const sendMessage = async () => {
        if (!input.trim() || isLoading) return

        const userMessage: Message = {
            id: `msg-${Date.now()}`,
            role: 'user',
            content: input.trim(),
        }

        setMessages(prev => [...prev, userMessage])
        setInput('')
        setIsLoading(true)

        try {
            // Try CopilotKit first, fallback to direct API
            await copilotSendMessage(userMessage.content)
        } catch (error) {
            // Fallback to direct backend API
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: userMessage.content })
                })

                const data = await response.json()

                const assistantMessage: Message = {
                    id: `msg-${Date.now() + 1}`,
                    role: 'assistant',
                    content: data.response || "I processed your request.",
                    toolCalls: data.tool_calls,
                }

                setMessages(prev => [...prev, assistantMessage])
            } catch (fallbackError) {
                const errorMessage: Message = {
                    id: `msg-${Date.now() + 1}`,
                    role: 'assistant',
                    content: "Connection error. Make sure the backend is running on port 8000.",
                }
                setMessages(prev => [...prev, errorMessage])
            }
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

    const handleSuggestionClick = (prompt: string) => {
        setInput(prompt)
        inputRef.current?.focus()
    }

    // Minimize view in focus mode
    if (focusMode) {
        return (
            <div className="glass rounded-2xl p-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse"></div>
                        <span className="text-sm text-zinc-400">Focus Mode Active</span>
                    </div>
                    <button
                        onClick={() => {
                            const { setFocusMode } = useCopilotContext()
                            setFocusMode(false)
                        }}
                        className="text-xs px-2 py-1 rounded bg-surface-light text-zinc-400 hover:text-white transition"
                    >
                        Exit Focus
                    </button>
                </div>
            </div>
        )
    }

    return (
        <div className="glass rounded-2xl flex flex-col h-[600px]">
            {/* Header */}
            <div className="px-4 py-3 border-b border-white/10">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg gradient-primary flex items-center justify-center">
                        <span className="text-lg">AI</span>
                    </div>
                    <div className="flex-1">
                        <h3 className="font-semibold text-white">AI Assistant</h3>
                        <p className="text-xs text-zinc-400">Powered by CopilotKit</p>
                    </div>
                    {/* Status indicator */}
                    <div className="flex items-center gap-1.5">
                        <div className={`w-2 h-2 rounded-full ${isLoading || copilotLoading ? 'bg-yellow-400 animate-pulse' : 'bg-green-400'}`}></div>
                        <span className="text-xs text-zinc-500">
                            {isLoading || copilotLoading ? 'Thinking...' : 'Ready'}
                        </span>
                    </div>
                </div>
            </div>

            {/* Context Bar - Shows current state */}
            <div className="px-4 py-2 bg-surface-light/50 border-b border-white/5">
                <div className="flex items-center gap-3 text-xs text-zinc-500">
                    <span className="flex items-center gap-1">
                        <span className="text-primary">Tab:</span>
                        {appState.activeTab}
                    </span>
                    {appState.timerStatus?.running && (
                        <span className="flex items-center gap-1 text-green-400">
                            <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse"></span>
                            Timer running
                        </span>
                    )}
                    {appState.tasks.length > 0 && (
                        <span>{appState.tasks.filter(t => t.status !== 'completed').length} tasks</span>
                    )}
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
                            {message.toolCalls && message.toolCalls.length > 0 && (
                                <div className="mt-3 pt-3 border-t border-white/10">
                                    <p className="text-xs text-zinc-400 mb-2">Actions performed:</p>
                                    {message.toolCalls.map((tc, i) => (
                                        <div key={i} className="text-xs bg-black/20 rounded px-2 py-1 mb-1 flex items-center gap-2">
                                            <span className="text-primary">{tc.tool}</span>
                                            {tc.result?.success !== undefined && (
                                                <span className={tc.result.success ? 'text-green-400' : 'text-red-400'}>
                                                    {tc.result.success ? 'Success' : 'Failed'}
                                                </span>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Streaming indicator */}
                            {message.isStreaming && (
                                <span className="inline-block w-2 h-4 bg-primary animate-pulse ml-1"></span>
                            )}
                        </div>
                    </div>
                ))}

                {/* Typing indicator */}
                {(isLoading || copilotLoading) && (
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

            {/* Quick Suggestions */}
            <div className="px-4 py-2 border-t border-white/10">
                <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
                    {COPILOT_CONFIG.chat.suggestions.map((suggestion, i) => (
                        <button
                            key={i}
                            onClick={() => handleSuggestionClick(suggestion.prompt)}
                            className="flex-shrink-0 text-xs px-3 py-1.5 rounded-full bg-surface-light hover:bg-primary/30 text-zinc-300 hover:text-white transition"
                        >
                            {suggestion.label}
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
                        placeholder={COPILOT_CONFIG.chat.placeholder}
                        className="flex-1 bg-surface-light rounded-xl px-4 py-3 text-white placeholder-zinc-500 outline-none focus:ring-2 focus:ring-primary/50 transition"
                        disabled={isLoading || copilotLoading}
                    />
                    <button
                        onClick={sendMessage}
                        disabled={isLoading || copilotLoading || !input.trim()}
                        className="px-4 py-3 rounded-xl gradient-primary text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-90 transition"
                    >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    )
}
