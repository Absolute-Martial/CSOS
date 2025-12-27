'use client'

import { useState, useRef, useEffect } from 'react'
import { useCopilotContext } from '@/providers/CopilotProvider'

// TODO: Remove or replace with a simpler context if needed
// For now, we keep simpler types as we transition out of CopilotKit
interface Message {
    id: string
    role: 'user' | 'assistant' | 'system'
    content: string
    toolCalls?: { tool: string; result: any }[]
    isStreaming?: boolean
}

export default function AIAssistant() {
    // Initial message
    const [messages, setMessages] = useState<Message[]>([
        {
            id: '1',
            role: 'assistant',
            content: "Hello! I'm here to help you with your studies and tasks.",
        }
    ])
    const [input, setInput] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const messagesEndRef = useRef<HTMLDivElement>(null)
    const inputRef = useRef<HTMLInputElement>(null)

    // TODO: Review if we still need this context or if it should be refactored
    const { appState } = useCopilotContext()

    const [threadId] = useState(() => `thread-${Date.now()}`)
    const [useStreaming, setUseStreaming] = useState(true)

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    const sendMessageStreaming = async (userContent: string) => {
        // Add placeholder for streaming response
        const assistantMsgId = `msg-${Date.now() + 1}`
        setMessages(prev => [...prev, {
            id: assistantMsgId,
            role: 'assistant',
            content: '',
            isStreaming: true,
        }])

        try {
            const response = await fetch(`/api/chat?message=${encodeURIComponent(userContent)}&thread_id=${threadId}`)

            if (!response.ok || !response.body) {
                throw new Error('Streaming failed')
            }

            const reader = response.body.getReader()
            const decoder = new TextDecoder()
            let accumulatedContent = ''

            while (true) {
                const { done, value } = await reader.read()
                if (done) break

                const chunk = decoder.decode(value, { stream: true })
                // Parse SSE format: data: {...}\n\n
                const lines = chunk.split('\n')
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6))
                            if (data.content) {
                                accumulatedContent += data.content
                                setMessages(prev => prev.map(m =>
                                    m.id === assistantMsgId
                                        ? { ...m, content: accumulatedContent }
                                        : m
                                ))
                            }
                            if (data.tool_calls) {
                                setMessages(prev => prev.map(m =>
                                    m.id === assistantMsgId
                                        ? { ...m, toolCalls: data.tool_calls }
                                        : m
                                ))
                            }
                        } catch {
                            // Skip malformed JSON
                        }
                    }
                }
            }

            // Mark streaming as complete
            setMessages(prev => prev.map(m =>
                m.id === assistantMsgId
                    ? { ...m, isStreaming: false }
                    : m
            ))
        } catch (error) {
            console.error('Streaming error:', error)
            // Fallback to non-streaming
            setMessages(prev => prev.filter(m => m.id !== assistantMsgId))
            await sendMessageNonStreaming(userContent)
        }
    }

    const sendMessageNonStreaming = async (userContent: string) => {
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: userContent, thread_id: threadId })
            })

            const data = await response.json()

            const assistantMessage: Message = {
                id: `msg-${Date.now() + 1}`,
                role: 'assistant',
                content: data.response || "I processed your request.",
                toolCalls: data.tool_calls,
            }

            setMessages(prev => [...prev, assistantMessage])
        } catch (error) {
            console.error(error)
            const errorMessage: Message = {
                id: `msg-${Date.now() + 1}`,
                role: 'assistant',
                content: "Connection error. Make sure the backend is running on port 8000.",
            }
            setMessages(prev => [...prev, errorMessage])
        }
    }

    const sendMessage = async () => {
        if (!input.trim() || isLoading) return

        const userMessage: Message = {
            id: `msg-${Date.now()}`,
            role: 'user',
            content: input.trim(),
        }

        setMessages(prev => [...prev, userMessage])
        const userContent = input.trim()
        setInput('')
        setIsLoading(true)

        try {
            if (useStreaming) {
                await sendMessageStreaming(userContent)
            } else {
                await sendMessageNonStreaming(userContent)
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

    // Removed focus mode logic related to CopilotContext toggles for now

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
                        <p className="text-xs text-zinc-400">Powered by LangGraph</p>
                    </div>
                    {/* Status indicator */}
                    <div className="flex items-center gap-1.5">
                        <div className={`w-2 h-2 rounded-full ${isLoading ? 'bg-yellow-400 animate-pulse' : 'bg-green-400'}`}></div>
                        <span className="text-xs text-zinc-500">
                            {isLoading ? 'Thinking...' : 'Ready'}
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
                        <span>{appState.tasks.filter((t: any) => t.status !== 'completed').length} tasks</span>
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

            {/* Input */}
            <div className="p-4 border-t border-white/10">
                <div className="flex gap-2">
                    <input
                        ref={inputRef}
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Ask anything..."
                        className="flex-1 bg-surface-light rounded-xl px-4 py-3 text-white placeholder-zinc-500 outline-none focus:ring-2 focus:ring-primary/50 transition"
                        disabled={isLoading}
                    />
                    <button
                        onClick={sendMessage}
                        disabled={isLoading || !input.trim()}
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

