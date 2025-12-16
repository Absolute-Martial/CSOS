'use client'

import { ReactNode, createContext, useContext, useState, useCallback } from 'react'
import { CopilotKit } from '@copilotkit/react-core'

// Agent type for switching between AI modes
export type AgentType = 'study_assistant' | 'scheduler'

// Types for app state shared with CopilotKit
export interface AppState {
    activeTab: string
    tasks: Task[]
    schedule: ScheduleData | null
    timerStatus: TimerStatus | null
    goals: Goal[]
    notifications: Notification[]
    userPreferences: UserPreferences
}

export interface Task {
    id: number
    title: string
    subject_code?: string
    color?: string
    scheduled_start?: string
    duration_mins?: number
    status: string
    is_deep_work?: boolean
}

export interface ScheduleData {
    date: string
    day: string
    classes: Array<{
        start: string
        end: string
        subject: string
        type: string
        room: string
    }>
    gaps: Array<{
        start: string
        end: string
        duration_mins: number
        is_deep_work_suitable: boolean
    }>
    tasks: Task[]
}

export interface TimerStatus {
    running: boolean
    session_id?: number
    elapsed_seconds?: number
    subject_code?: string
    subject_name?: string
    color?: string
    title?: string
    started_at?: string
}

export interface Goal {
    id: number
    title: string
    description?: string
    target_value?: number
    current_value: number
    unit?: string
    deadline?: string
    priority: number
    completed: boolean
    progress_percent: number
}

export interface Notification {
    id: string
    type: 'success' | 'info' | 'warning' | 'error' | 'achievement'
    title: string
    message: string
    timestamp: Date
}

export interface UserPreferences {
    sleepStart: string
    sleepEnd: string
    deepWorkDuration: number
    breakDuration: number
    theme: 'dark' | 'light'
}

interface CopilotContextValue {
    appState: AppState
    updateAppState: (updates: Partial<AppState>) => void
    addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) => void
    clearNotification: (id: string) => void
    setActiveTab: (tab: string) => void
    currentAgent: AgentType
    switchAgent: (agent: AgentType) => void
    highlightedTaskId: number | null
    setHighlightedTaskId: (id: number | null) => void
    focusMode: boolean
    setFocusMode: (enabled: boolean) => void
    showScheduleConfirmation: (changes: ScheduleChange[]) => Promise<boolean>
    pendingScheduleChanges: ScheduleChange[]
    confirmScheduleChanges: () => void
    cancelScheduleChanges: () => void
}

export interface ScheduleChange {
    type: 'add' | 'move' | 'delete'
    task: {
        id?: number
        title: string
        start?: string
        end?: string
        subject?: string
    }
    from?: { start: string; end: string }
    to?: { start: string; end: string }
    reason?: string
}

const CopilotContext = createContext<CopilotContextValue | null>(null)

export function useCopilotContext() {
    const context = useContext(CopilotContext)
    if (!context) {
        throw new Error('useCopilotContext must be used within CopilotProvider')
    }
    return context
}

interface CopilotProviderProps {
    children: ReactNode
}

const defaultPreferences: UserPreferences = {
    sleepStart: '23:00',
    sleepEnd: '06:00',
    deepWorkDuration: 90,
    breakDuration: 15,
    theme: 'dark'
}

export default function CopilotProvider({ children }: CopilotProviderProps) {
    const [appState, setAppState] = useState<AppState>({
        activeTab: 'today',
        tasks: [],
        schedule: null,
        timerStatus: null,
        goals: [],
        notifications: [],
        userPreferences: defaultPreferences
    })

    const [currentAgent, setCurrentAgent] = useState<AgentType>('study_assistant')
    const [highlightedTaskId, setHighlightedTaskId] = useState<number | null>(null)
    const [focusMode, setFocusMode] = useState(false)
    const [pendingScheduleChanges, setPendingScheduleChanges] = useState<ScheduleChange[]>([])
    const [scheduleConfirmResolver, setScheduleConfirmResolver] = useState<((value: boolean) => void) | null>(null)

    const updateAppState = useCallback((updates: Partial<AppState>) => {
        setAppState(prev => ({ ...prev, ...updates }))
    }, [])

    const addNotification = useCallback((notification: Omit<Notification, 'id' | 'timestamp'>) => {
        const newNotification: Notification = {
            ...notification,
            id: `notif-${Date.now()}`,
            timestamp: new Date()
        }
        setAppState(prev => ({
            ...prev,
            notifications: [...prev.notifications, newNotification]
        }))

        // Auto-remove after 5 seconds for non-achievement notifications
        if (notification.type !== 'achievement') {
            setTimeout(() => {
                clearNotification(newNotification.id)
            }, 5000)
        }
    }, [])

    const clearNotification = useCallback((id: string) => {
        setAppState(prev => ({
            ...prev,
            notifications: prev.notifications.filter(n => n.id !== id)
        }))
    }, [])

    const setActiveTab = useCallback((tab: string) => {
        setAppState(prev => ({ ...prev, activeTab: tab }))
    }, [])

    const switchAgent = useCallback((agent: AgentType) => {
        setCurrentAgent(agent)
    }, [])

    const showScheduleConfirmation = useCallback((changes: ScheduleChange[]): Promise<boolean> => {
        return new Promise((resolve) => {
            setPendingScheduleChanges(changes)
            setScheduleConfirmResolver(() => resolve)
        })
    }, [])

    const confirmScheduleChanges = useCallback(() => {
        if (scheduleConfirmResolver) {
            scheduleConfirmResolver(true)
            setScheduleConfirmResolver(null)
            setPendingScheduleChanges([])
        }
    }, [scheduleConfirmResolver])

    const cancelScheduleChanges = useCallback(() => {
        if (scheduleConfirmResolver) {
            scheduleConfirmResolver(false)
            setScheduleConfirmResolver(null)
            setPendingScheduleChanges([])
        }
    }, [scheduleConfirmResolver])

    const contextValue: CopilotContextValue = {
        appState,
        updateAppState,
        addNotification,
        clearNotification,
        setActiveTab,
        currentAgent,
        switchAgent,
        highlightedTaskId,
        setHighlightedTaskId,
        focusMode,
        setFocusMode,
        showScheduleConfirmation,
        pendingScheduleChanges,
        confirmScheduleChanges,
        cancelScheduleChanges
    }

    return (
        <CopilotContext.Provider value={contextValue}>
            <CopilotKit runtimeUrl="/api/copilotkit">
                {children}
            </CopilotKit>
        </CopilotContext.Provider>
    )
}
