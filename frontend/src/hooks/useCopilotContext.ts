'use client'

import { useEffect, useCallback } from 'react'
import { useCopilotReadable } from '@copilotkit/react-core'
import { useCopilotContext, Task, ScheduleData, TimerStatus, Goal } from '@/providers/CopilotProvider'

/**
 * Hook that syncs app state with CopilotKit
 * Makes application data readable by the AI assistant
 */
export function useCopilotContextSync() {
    const { appState, updateAppState } = useCopilotContext()

    // Fetch and sync tasks
    const fetchTasks = useCallback(async () => {
        try {
            const res = await fetch('/api/tasks/today')
            if (res.ok) {
                const data = await res.json()
                updateAppState({ tasks: data })
            }
        } catch (error) {
            console.error('Failed to fetch tasks:', error)
        }
    }, [updateAppState])

    // Fetch and sync schedule
    const fetchSchedule = useCallback(async () => {
        try {
            const res = await fetch('/api/schedule/today')
            if (res.ok) {
                const data = await res.json()
                const schedule: ScheduleData = {
                    date: data.date,
                    day: data.day,
                    classes: data.timetable?.classes || [],
                    gaps: data.gaps?.slots || [],
                    tasks: data.tasks?.scheduled || []
                }
                updateAppState({ schedule })
            }
        } catch (error) {
            console.error('Failed to fetch schedule:', error)
        }
    }, [updateAppState])

    // Fetch and sync timer status
    const fetchTimerStatus = useCallback(async () => {
        try {
            const res = await fetch('/api/timer/status')
            if (res.ok) {
                const data = await res.json()
                updateAppState({ timerStatus: data })
            }
        } catch (error) {
            console.error('Failed to fetch timer status:', error)
        }
    }, [updateAppState])

    // Fetch and sync goals
    const fetchGoals = useCallback(async () => {
        try {
            const res = await fetch('/api/goals')
            if (res.ok) {
                const data = await res.json()
                updateAppState({ goals: data })
            }
        } catch (error) {
            console.error('Failed to fetch goals:', error)
        }
    }, [updateAppState])

    // Initial data fetch
    useEffect(() => {
        fetchTasks()
        fetchSchedule()
        fetchTimerStatus()
        fetchGoals()

        // Refresh data periodically
        const interval = setInterval(() => {
            fetchTimerStatus()
        }, 30000) // Every 30 seconds

        return () => clearInterval(interval)
    }, [fetchTasks, fetchSchedule, fetchTimerStatus, fetchGoals])

    // Make current tab readable
    useCopilotReadable({
        description: 'The currently active tab in the application',
        value: appState.activeTab
    })

    // Make tasks readable
    useCopilotReadable({
        description: 'List of tasks for today including their status, subject, and duration',
        value: JSON.stringify({
            count: appState.tasks.length,
            pending: appState.tasks.filter(t => t.status !== 'completed').length,
            completed: appState.tasks.filter(t => t.status === 'completed').length,
            tasks: appState.tasks.map(t => ({
                id: t.id,
                title: t.title,
                subject: t.subject_code,
                status: t.status,
                duration: t.duration_mins,
                isDeepWork: t.is_deep_work
            }))
        })
    })

    // Make schedule readable
    useCopilotReadable({
        description: 'Today\'s schedule including university classes and available study gaps',
        value: appState.schedule ? JSON.stringify({
            date: appState.schedule.date,
            day: appState.schedule.day,
            classes: appState.schedule.classes.map(c => ({
                time: `${c.start}-${c.end}`,
                subject: c.subject,
                type: c.type,
                room: c.room
            })),
            gaps: appState.schedule.gaps.map(g => ({
                time: `${g.start}-${g.end}`,
                duration: g.duration_mins,
                suitableForDeepWork: g.is_deep_work_suitable
            })),
            totalDeepWorkMins: appState.schedule.gaps
                .filter(g => g.is_deep_work_suitable)
                .reduce((sum, g) => sum + g.duration_mins, 0)
        }) : 'No schedule data available'
    })

    // Make timer status readable
    useCopilotReadable({
        description: 'Current study timer status - whether running, elapsed time, and subject',
        value: appState.timerStatus ? JSON.stringify({
            running: appState.timerStatus.running,
            elapsedMinutes: appState.timerStatus.elapsed_seconds
                ? Math.floor(appState.timerStatus.elapsed_seconds / 60)
                : 0,
            subject: appState.timerStatus.subject_code || 'General',
            isDeepWork: (appState.timerStatus.elapsed_seconds || 0) >= 5400
        }) : 'Timer not running'
    })

    // Make goals readable
    useCopilotReadable({
        description: 'User\'s study goals with progress tracking',
        value: JSON.stringify({
            total: appState.goals.length,
            active: appState.goals.filter(g => !g.completed).length,
            completed: appState.goals.filter(g => g.completed).length,
            goals: appState.goals.map(g => ({
                id: g.id,
                title: g.title,
                progress: g.progress_percent,
                target: g.target_value,
                current: g.current_value,
                unit: g.unit,
                deadline: g.deadline,
                priority: g.priority,
                completed: g.completed
            }))
        })
    })

    // Make user preferences readable
    useCopilotReadable({
        description: 'User preferences for scheduling and study sessions',
        value: JSON.stringify(appState.userPreferences)
    })

    // Make current time readable
    useCopilotReadable({
        description: 'Current date and time for context-aware responses',
        value: JSON.stringify({
            date: new Date().toISOString().split('T')[0],
            time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false }),
            dayOfWeek: new Date().toLocaleDateString('en-US', { weekday: 'long' }),
            hour: new Date().getHours()
        })
    })

    // Return refresh functions for manual updates
    return {
        refreshTasks: fetchTasks,
        refreshSchedule: fetchSchedule,
        refreshTimerStatus: fetchTimerStatus,
        refreshGoals: fetchGoals,
        refreshAll: () => {
            fetchTasks()
            fetchSchedule()
            fetchTimerStatus()
            fetchGoals()
        }
    }
}

/**
 * Hook for accessing specific readable context values
 */
export function useStudyContext() {
    const { appState } = useCopilotContext()

    const currentHour = new Date().getHours()

    // Calculate energy level based on time of day
    const getEnergyLevel = (): 'high' | 'medium' | 'low' => {
        if ((currentHour >= 8 && currentHour < 10) || (currentHour >= 16 && currentHour < 18)) {
            return 'high'
        }
        if ((currentHour >= 6 && currentHour < 8) || (currentHour >= 10 && currentHour < 12) ||
            (currentHour >= 14 && currentHour < 16) || (currentHour >= 18 && currentHour < 20)) {
            return 'medium'
        }
        return 'low'
    }

    // Get recommended task type based on energy
    const getRecommendedTaskType = (): string => {
        const energy = getEnergyLevel()
        switch (energy) {
            case 'high':
                return 'Deep work, challenging problems, new concepts'
            case 'medium':
                return 'Regular study, assignments, reading'
            case 'low':
                return 'Review, light reading, planning'
        }
    }

    // Calculate study metrics
    const studyMetrics = {
        pendingTasks: appState.tasks.filter(t => t.status !== 'completed').length,
        completedTasks: appState.tasks.filter(t => t.status === 'completed').length,
        completionRate: appState.tasks.length > 0
            ? Math.round((appState.tasks.filter(t => t.status === 'completed').length / appState.tasks.length) * 100)
            : 0,
        deepWorkMinutes: appState.schedule?.gaps
            .filter(g => g.is_deep_work_suitable)
            .reduce((sum, g) => sum + g.duration_mins, 0) || 0,
        activeGoals: appState.goals.filter(g => !g.completed).length,
        isTimerRunning: appState.timerStatus?.running || false,
        currentSubject: appState.timerStatus?.subject_code || null,
        energyLevel: getEnergyLevel(),
        recommendedTaskType: getRecommendedTaskType()
    }

    return {
        ...studyMetrics,
        schedule: appState.schedule,
        tasks: appState.tasks,
        goals: appState.goals,
        timerStatus: appState.timerStatus
    }
}
