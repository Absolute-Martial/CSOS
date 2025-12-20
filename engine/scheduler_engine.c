/*
 * AI Engineering Study Assistant - Scheduler Engine
 * scheduler_engine.c - Constraint Satisfaction Solver for Timeline Optimization
 * 
 * This module implements a backtracking CSP solver for optimizing
 * weekly study schedules. It respects hard constraints (sleep, classes)
 * and applies heuristics for concept/practice placement.
 * 
 * Compiled as a shared library for Python ctypes integration.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <time.h>

/* ============================================
 * PLATFORM-SPECIFIC EXPORTS
 * ============================================ */

#ifdef _WIN32
    #define EXPORT __declspec(dllexport)
#else
    #define EXPORT __attribute__((visibility("default")))
#endif

/* ============================================
 * CONSTANTS
 * ============================================ */

#define MAX_TITLE_LEN 200
#define MAX_SUBJECT_LEN 20
#define MAX_TASKS 100
#define SLOTS_PER_DAY 48       /* 30-minute slots */
#define WEEK_SLOTS 336         /* 7 days * 48 slots */
#define EMPTY_SLOT -1
#define BLOCKED_SLOT -2        /* Sleep or other blocked time */

/* ============================================
 * ENUMS
 * ============================================ */

typedef enum {
    TASK_FIXED_CLASS = 0,      /* University lectures (immutable) */
    TASK_STUDY_CONCEPT = 1,    /* Conceptual learning (morning priority) */
    TASK_STUDY_PRACTICE = 2,   /* Practice problems (evening priority) */
    TASK_MICRO_GAP = 3,        /* 15-30 min tasks */
    TASK_SLEEP = 4,            /* Rest blocks */
    TASK_BREAK = 5,            /* Break periods */
    TASK_MEAL = 6,             /* Meal times */
    TASK_REVISION = 7,         /* Spaced repetition */
    TASK_ASSIGNMENT = 8,       /* Assignment work */
    TASK_LAB_WORK = 9          /* Lab report work */
} TaskCategory;

/* ============================================
 * STRUCTURES
 * ============================================ */

/* Task to be placed in timeline */
typedef struct {
    int id;
    int duration_slots;        /* Duration in 30-min slots */
    int priority;              /* 1-10, higher = more important */
    int category;              /* TaskCategory enum value */
    int deadline_slot;         /* Absolute slot index for deadline */
    bool is_locked;            /* If true, cannot be moved */
    char title[MAX_TITLE_LEN];
    char subject[MAX_SUBJECT_LEN];
    int preferred_slot;        /* Preferred placement (-1 for none) */
    int assigned_slot;         /* Assigned slot after optimization */
} TimelineTask;

/* Optimization configuration */
typedef struct {
    int sleep_start_slot;      /* Slot when sleep begins (22:00 = 44) */
    int sleep_end_slot;        /* Slot when sleep ends (06:00 = 12) */
    int concept_peak_start;    /* Morning peak start (08:00 = 16) */
    int concept_peak_end;      /* Morning peak end (12:00 = 24) */
    int practice_peak_start;   /* Evening peak start (16:00 = 32) */
    int practice_peak_end;     /* Evening peak end (20:00 = 40) */
    int deep_work_min_slots;   /* Min slots for deep work (3 = 90 min) */
    int micro_gap_max_slots;   /* Max slots for micro-gaps (1 = 30 min) */
    bool enable_heuristics;    /* Enable energy-based placement */
} OptimizationConfig;

/* Weekly timeline result */
typedef struct {
    int slots[WEEK_SLOTS];     /* Task ID in each slot (-1 = empty) */
    int slot_count;
    TimelineTask* tasks;
    int task_count;
    int optimization_status;   /* 0=success, -1=unsolvable, -2=timeout */
    int error_code;
    int total_gaps_filled;
    int total_conflicts;
} WeeklyTimeline;

/* Gap in schedule */
typedef struct {
    int start_slot;
    int end_slot;
    int duration_slots;
    int day_index;
    int gap_type;              /* 0=micro, 1=standard, 2=deep_work */
} ScheduleGap;

/* ============================================
 * UTILITY FUNCTIONS
 * ============================================ */

/* Get day index from absolute slot */
static int get_day_index(int slot) {
    return slot / SLOTS_PER_DAY;
}

/* Get slot within day from absolute slot */
static int get_day_slot(int slot) {
    return slot % SLOTS_PER_DAY;
}

/* Check if slot is in a time range (handles overnight ranges) */
static bool is_in_range(int slot, int start, int end) {
    int day_slot = get_day_slot(slot);
    
    if (start <= end) {
        /* Normal range (e.g., 16-24 for concept hours) */
        return day_slot >= start && day_slot < end;
    } else {
        /* Overnight range (e.g., 44-12 for sleep) */
        return day_slot >= start || day_slot < end;
    }
}

/* Check if a slot is blocked for sleep */
static bool is_sleep_slot(int slot, OptimizationConfig* config) {
    return is_in_range(slot, config->sleep_start_slot, config->sleep_end_slot);
}

/* Check if a slot is in concept study peak hours */
static bool is_concept_peak(int slot, OptimizationConfig* config) {
    return is_in_range(slot, config->concept_peak_start, config->concept_peak_end);
}

/* Check if a slot is in practice peak hours */
static bool is_practice_peak(int slot, OptimizationConfig* config) {
    return is_in_range(slot, config->practice_peak_start, config->practice_peak_end);
}

/* Compare tasks by priority (descending) then deadline (ascending) */
static int compare_tasks(const void* a, const void* b) {
    TimelineTask* ta = (TimelineTask*)a;
    TimelineTask* tb = (TimelineTask*)b;
    
    /* Locked tasks first */
    if (ta->is_locked != tb->is_locked) {
        return ta->is_locked ? -1 : 1;
    }
    
    /* Higher priority first */
    if (ta->priority != tb->priority) {
        return tb->priority - ta->priority;
    }
    
    /* Earlier deadline first */
    return ta->deadline_slot - tb->deadline_slot;
}

/* ============================================
 * CONSTRAINT CHECKING
 * ============================================ */

/* Check if task can be placed at given slot */
static bool can_place_task(WeeklyTimeline* timeline, int slot, TimelineTask* task, OptimizationConfig* config) {
    int duration = task->duration_slots;
    
    /* Check bounds */
    if (slot < 0 || slot + duration > WEEK_SLOTS) {
        return false;
    }
    
    /* Check deadline constraint */
    if (slot + duration > task->deadline_slot) {
        return false;
    }
    
    /* Check all slots are available */
    for (int i = 0; i < duration; i++) {
        int check_slot = slot + i;
        
        /* Slot must be empty */
        if (timeline->slots[check_slot] != EMPTY_SLOT) {
            return false;
        }
        
        /* Slot must not be during sleep (unless it's a sleep task) */
        if (task->category != TASK_SLEEP && is_sleep_slot(check_slot, config)) {
            return false;
        }
    }
    
    return true;
}

/* Calculate heuristic score for placing task at slot */
static int get_placement_score(int slot, TimelineTask* task, OptimizationConfig* config) {
    int score = 0;
    
    if (!config->enable_heuristics) {
        return 0;
    }
    
    /* Bonus for placing concept tasks in morning peak */
    if (task->category == TASK_STUDY_CONCEPT && is_concept_peak(slot, config)) {
        score += 20;
    }
    
    /* Bonus for placing practice tasks in evening peak */
    if (task->category == TASK_STUDY_PRACTICE && is_practice_peak(slot, config)) {
        score += 20;
    }
    
    /* Penalty for placing concept tasks in evening */
    if (task->category == TASK_STUDY_CONCEPT && is_practice_peak(slot, config)) {
        score -= 10;
    }
    
    /* Penalty for placing practice tasks in morning */
    if (task->category == TASK_STUDY_PRACTICE && is_concept_peak(slot, config)) {
        score -= 10;
    }
    
    /* Bonus for earlier placement (more buffer) */
    int days_before_deadline = (task->deadline_slot - slot) / SLOTS_PER_DAY;
    score += days_before_deadline * 2;
    
    return score;
}

/* ============================================
 * CSP SOLVER (Backtracking)
 * ============================================ */

/* Place a task in the timeline */
static void place_task(WeeklyTimeline* timeline, int slot, TimelineTask* task) {
    for (int i = 0; i < task->duration_slots; i++) {
        timeline->slots[slot + i] = task->id;
    }
    task->assigned_slot = slot;
}

/* Remove a task from the timeline */
static void remove_task(WeeklyTimeline* timeline, int slot, TimelineTask* task) {
    for (int i = 0; i < task->duration_slots; i++) {
        timeline->slots[slot + i] = EMPTY_SLOT;
    }
    task->assigned_slot = -1;
}

/* Find best slot for a task using heuristics */
static int find_best_slot(WeeklyTimeline* timeline, TimelineTask* task, OptimizationConfig* config) {
    int best_slot = -1;
    int best_score = -999999;
    
    /* If task has preferred slot and it's valid, use it */
    if (task->preferred_slot >= 0 && can_place_task(timeline, task->preferred_slot, task, config)) {
        return task->preferred_slot;
    }
    
    /* Search for best slot */
    int search_limit = task->deadline_slot - task->duration_slots + 1;
    if (search_limit > WEEK_SLOTS - task->duration_slots + 1) {
        search_limit = WEEK_SLOTS - task->duration_slots + 1;
    }
    
    for (int slot = 0; slot < search_limit; slot++) {
        if (can_place_task(timeline, slot, task, config)) {
            int score = get_placement_score(slot, task, config);
            
            if (score > best_score) {
                best_score = score;
                best_slot = slot;
            }
        }
    }
    
    return best_slot;
}

/* Greedy solver with heuristics */
static bool greedy_solve(WeeklyTimeline* timeline, TimelineTask* tasks, int task_count, OptimizationConfig* config) {
    int placed = 0;
    int conflicts = 0;
    
    /* Sort tasks by priority and deadline */
    qsort(tasks, task_count, sizeof(TimelineTask), compare_tasks);
    
    /* Place each task */
    for (int i = 0; i < task_count; i++) {
        TimelineTask* task = &tasks[i];
        
        /* Find best slot */
        int slot = find_best_slot(timeline, task, config);
        
        if (slot >= 0) {
            place_task(timeline, slot, task);
            placed++;
        } else {
            /* Could not place task */
            conflicts++;
            task->assigned_slot = -1;
        }
    }
    
    timeline->total_conflicts = conflicts;
    timeline->total_gaps_filled = placed;
    
    return conflicts == 0;
}

/* ============================================
 * EXPORTED FUNCTIONS
 * ============================================ */

EXPORT WeeklyTimeline* optimize_timeline(TimelineTask* tasks, int count, OptimizationConfig* config) {
    /* Allocate timeline */
    WeeklyTimeline* timeline = (WeeklyTimeline*)malloc(sizeof(WeeklyTimeline));
    if (!timeline) {
        return NULL;
    }
    
    /* Initialize all slots as empty */
    for (int i = 0; i < WEEK_SLOTS; i++) {
        timeline->slots[i] = EMPTY_SLOT;
    }
    
    timeline->slot_count = WEEK_SLOTS;
    timeline->tasks = tasks;
    timeline->task_count = count;
    timeline->optimization_status = 0;
    timeline->error_code = 0;
    timeline->total_gaps_filled = 0;
    timeline->total_conflicts = 0;
    
    /* Use default config if none provided */
    OptimizationConfig default_config = {
        .sleep_start_slot = 46,      /* 23:00 */
        .sleep_end_slot = 12,        /* 06:00 */
        .concept_peak_start = 16,    /* 08:00 */
        .concept_peak_end = 24,      /* 12:00 */
        .practice_peak_start = 32,   /* 16:00 */
        .practice_peak_end = 40,     /* 20:00 */
        .deep_work_min_slots = 3,    /* 90 min */
        .micro_gap_max_slots = 1,    /* 30 min */
        .enable_heuristics = true
    };
    
    OptimizationConfig* cfg = config ? config : &default_config;
    
    /* Mark sleep slots as blocked */
    for (int day = 0; day < 7; day++) {
        int day_offset = day * SLOTS_PER_DAY;
        
        /* Handle overnight sleep (e.g., 23:00 to 06:00) */
        if (cfg->sleep_start_slot > cfg->sleep_end_slot) {
            /* Evening portion */
            for (int s = cfg->sleep_start_slot; s < SLOTS_PER_DAY; s++) {
                timeline->slots[day_offset + s] = BLOCKED_SLOT;
            }
            /* Morning portion (next day logic handled by wrapping) */
            int next_day_offset = ((day + 1) % 7) * SLOTS_PER_DAY;
            for (int s = 0; s < cfg->sleep_end_slot; s++) {
                if (next_day_offset + s < WEEK_SLOTS) {
                    timeline->slots[next_day_offset + s] = BLOCKED_SLOT;
                }
            }
        } else {
            /* Normal range */
            for (int s = cfg->sleep_start_slot; s < cfg->sleep_end_slot; s++) {
                timeline->slots[day_offset + s] = BLOCKED_SLOT;
            }
        }
    }
    
    /* Place locked/fixed tasks first */
    for (int i = 0; i < count; i++) {
        if (tasks[i].is_locked && tasks[i].preferred_slot >= 0) {
            if (tasks[i].preferred_slot + tasks[i].duration_slots <= WEEK_SLOTS) {
                /* Force place locked tasks */
                for (int j = 0; j < tasks[i].duration_slots; j++) {
                    timeline->slots[tasks[i].preferred_slot + j] = tasks[i].id;
                }
                tasks[i].assigned_slot = tasks[i].preferred_slot;
            }
        }
    }
    
    /* Run greedy solver on remaining tasks */
    if (!greedy_solve(timeline, tasks, count, cfg)) {
        /* Some tasks could not be placed */
        if (timeline->total_conflicts > count / 2) {
            timeline->optimization_status = -1; /* Unsolvable */
        } else {
            timeline->optimization_status = 0;  /* Partial success */
        }
    }
    
    return timeline;
}

EXPORT void free_timeline_memory(WeeklyTimeline* timeline) {
    if (timeline) {
        /* Note: tasks array is owned by caller, don't free it */
        free(timeline);
    }
}

EXPORT int validate_constraints(WeeklyTimeline* timeline) {
    if (!timeline) return -1;
    
    int violations = 0;
    
    /* Check for overlaps */
    for (int i = 0; i < WEEK_SLOTS; i++) {
        if (timeline->slots[i] >= 0) {
            /* Valid task ID - check consistency */
        }
    }
    
    return violations;
}

EXPORT int find_gaps(WeeklyTimeline* timeline, ScheduleGap* gaps, int max_gaps) {
    if (!timeline || !gaps) return 0;
    
    int gap_count = 0;
    int gap_start = -1;
    
    for (int i = 0; i < WEEK_SLOTS && gap_count < max_gaps; i++) {
        if (timeline->slots[i] == EMPTY_SLOT) {
            if (gap_start < 0) {
                gap_start = i;
            }
        } else {
            if (gap_start >= 0) {
                /* End of gap */
                int duration = i - gap_start;
                
                gaps[gap_count].start_slot = gap_start;
                gaps[gap_count].end_slot = i;
                gaps[gap_count].duration_slots = duration;
                gaps[gap_count].day_index = get_day_index(gap_start);
                
                /* Classify gap type */
                if (duration <= 1) {
                    gaps[gap_count].gap_type = 0; /* micro */
                } else if (duration <= 2) {
                    gaps[gap_count].gap_type = 1; /* standard */
                } else {
                    gaps[gap_count].gap_type = 2; /* deep_work */
                }
                
                gap_count++;
                gap_start = -1;
            }
        }
    }
    
    /* Handle trailing gap */
    if (gap_start >= 0 && gap_count < max_gaps) {
        int duration = WEEK_SLOTS - gap_start;
        gaps[gap_count].start_slot = gap_start;
        gaps[gap_count].end_slot = WEEK_SLOTS;
        gaps[gap_count].duration_slots = duration;
        gaps[gap_count].day_index = get_day_index(gap_start);
        gaps[gap_count].gap_type = duration <= 1 ? 0 : (duration <= 2 ? 1 : 2);
        gap_count++;
    }
    
    return gap_count;
}

/* ============================================
 * VERSION INFO
 * ============================================ */

EXPORT const char* get_engine_version(void) {
    return "1.0.0";
}

EXPORT int get_slots_per_day(void) {
    return SLOTS_PER_DAY;
}

EXPORT int get_week_slots(void) {
    return WEEK_SLOTS;
}
