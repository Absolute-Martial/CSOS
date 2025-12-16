/**
 * CopilotKit Configuration
 * Central configuration for CopilotKit integration with Personal Engineering OS
 */

export const COPILOT_CONFIG = {
    // Runtime endpoint - proxied through Next.js API routes
    runtimeUrl: '/api/copilotkit',

    // Default agent for study management
    defaultAgent: 'study_assistant',

    // Agent configurations
    agents: {
        study_assistant: {
            name: 'Study Assistant',
            description: 'AI-powered study management assistant for KU Engineering students',
            systemPrompt: `You are Study Assistant, an AI helper for KU Engineering students using the Personal Engineering OS.

Your capabilities:
- Schedule management: View and modify study schedules, find deep work slots
- Task tracking: Create, update, and manage study tasks
- Lab report tracking: Monitor lab report deadlines and status
- Study timer: Start/stop study sessions, track deep work
- Goal management: Create and track study goals with progress
- Spaced repetition: Schedule and track revision sessions

Behavioral guidelines:
- Be concise and action-oriented
- Proactively suggest optimizations based on the user's schedule
- Use the provided tools to make actual changes when requested
- Always confirm before making significant schedule changes
- Celebrate achievements and progress
- Match task difficulty to energy levels throughout the day

Context awareness:
- You have access to the user's full schedule including KU timetable
- You can see available gaps for deep work
- You know about pending deadlines and revisions
- You track study streaks and points`
        },
        scheduler: {
            name: 'Schedule Optimizer',
            description: 'Specialized agent for schedule optimization',
            systemPrompt: 'You are a scheduling expert. Focus on optimizing study schedules based on energy levels, deadlines, and deep work opportunities.'
        }
    },

    // Chat UI configuration
    chat: {
        initialMessage: "Hello! I'm your Engineering OS assistant. I can help you manage your schedule, track revisions, and optimize your study time.",
        suggestions: [
            { label: 'Morning briefing', prompt: 'Give me my morning briefing' },
            { label: 'What to revise?', prompt: 'What should I revise today?' },
            { label: 'Find free time', prompt: 'Analyze my schedule for deep work gaps' },
            { label: 'Start timer', prompt: 'Start a study timer for 45 minutes' },
            { label: 'Lab reports', prompt: 'Show me my pending lab reports' },
        ],
        placeholder: 'Type a command...'
    },

    // Tool categories for organization
    toolCategories: {
        schedule: ['get_today_schedule', 'get_week_schedule', 'find_deep_work_slots', 'schedule_event_prep'],
        tasks: ['create_task', 'update_task', 'delete_task', 'get_tasks'],
        timer: ['start_study_timer', 'stop_study_timer', 'get_timer_status', 'get_study_stats'],
        labs: ['get_lab_reports', 'add_lab_report', 'update_lab_report'],
        goals: ['create_study_goal', 'update_goal_progress', 'get_goals', 'get_goals_summary'],
        memory: ['remember_user_info', 'recall_memories', 'forget_memory'],
    },

    // Feature flags
    features: {
        voiceInput: false,
        streamResponses: true,
        showToolCalls: true,
        confirmBeforeAction: true,
        achievements: true,
    }
}

// Type definitions
export interface CopilotAgent {
    name: string
    description: string
    systemPrompt: string
}

export interface ChatSuggestion {
    label: string
    prompt: string
}

export type AgentType = keyof typeof COPILOT_CONFIG.agents
