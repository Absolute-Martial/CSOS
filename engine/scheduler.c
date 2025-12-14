/*
 * Personal Engineering OS - Scheduler Engine
 * scheduler.c - Main implementation
 * COMP 102 aligned: malloc/free, structs, binary I/O
 */

#include "scheduler.h"

/* ============================================
 * MEMORY MANAGEMENT
 * ============================================ */

DailySchedule* schedule_create(int capacity) {
    DailySchedule* schedule = (DailySchedule*)malloc(sizeof(DailySchedule));
    if (!schedule) {
        fprintf(stderr, "Error: Failed to allocate schedule\n");
        return NULL;
    }
    
    schedule->tasks = (Task*)malloc(sizeof(Task) * capacity);
    if (!schedule->tasks) {
        fprintf(stderr, "Error: Failed to allocate tasks array\n");
        free(schedule);
        return NULL;
    }
    
    schedule->gaps = (ScheduleGap*)malloc(sizeof(ScheduleGap) * capacity);
    if (!schedule->gaps) {
        fprintf(stderr, "Error: Failed to allocate gaps array\n");
        free(schedule->tasks);
        free(schedule);
        return NULL;
    }
    
    schedule->task_count = 0;
    schedule->gap_count = 0;
    schedule->capacity = capacity;
    
    return schedule;
}

void schedule_destroy(DailySchedule* schedule) {
    if (schedule) {
        free(schedule->tasks);
        free(schedule->gaps);
        free(schedule);
    }
}

PriorityQueue* pq_create(int capacity) {
    PriorityQueue* pq = (PriorityQueue*)malloc(sizeof(PriorityQueue));
    if (!pq) {
        fprintf(stderr, "Error: Failed to allocate priority queue\n");
        return NULL;
    }
    
    pq->reports = (LabReport*)malloc(sizeof(LabReport) * capacity);
    if (!pq->reports) {
        fprintf(stderr, "Error: Failed to allocate reports array\n");
        free(pq);
        return NULL;
    }
    
    pq->size = 0;
    pq->capacity = capacity;
    
    return pq;
}

void pq_destroy(PriorityQueue* pq) {
    if (pq) {
        free(pq->reports);
        free(pq);
    }
}

/* ============================================
 * UTILITY FUNCTIONS
 * ============================================ */

int time_to_minutes(TimeSlot t) {
    return t.hour * 60 + t.minute;
}

TimeSlot minutes_to_time(int minutes) {
    TimeSlot t;
    t.hour = minutes / 60;
    t.minute = minutes % 60;
    return t;
}

int compare_time(TimeSlot a, TimeSlot b) {
    int mins_a = time_to_minutes(a);
    int mins_b = time_to_minutes(b);
    return mins_a - mins_b;
}

/* ============================================
 * SCHEDULE OPERATIONS
 * ============================================ */

int schedule_add_task(DailySchedule* schedule, Task task) {
    if (schedule->task_count >= schedule->capacity) {
        fprintf(stderr, "Error: Schedule is full\n");
        return -1;
    }
    
    task.id = schedule->task_count + 1;
    schedule->tasks[schedule->task_count] = task;
    schedule->task_count++;
    
    return task.id;
}

int schedule_remove_task(DailySchedule* schedule, int task_id) {
    for (int i = 0; i < schedule->task_count; i++) {
        if (schedule->tasks[i].id == task_id) {
            /* Shift remaining tasks */
            for (int j = i; j < schedule->task_count - 1; j++) {
                schedule->tasks[j] = schedule->tasks[j + 1];
            }
            schedule->task_count--;
            return 0;
        }
    }
    return -1;
}

/* Sort tasks by start time (bubble sort for simplicity) */
void schedule_sort_by_time(DailySchedule* schedule) {
    for (int i = 0; i < schedule->task_count - 1; i++) {
        for (int j = 0; j < schedule->task_count - i - 1; j++) {
            if (compare_time(schedule->tasks[j].start_time, 
                           schedule->tasks[j + 1].start_time) > 0) {
                Task temp = schedule->tasks[j];
                schedule->tasks[j] = schedule->tasks[j + 1];
                schedule->tasks[j + 1] = temp;
            }
        }
    }
}

/* ============================================
 * DEEP WORK GAP ANALYSIS
 * ============================================ */

int analyze_gaps(DailySchedule* schedule) {
    schedule_sort_by_time(schedule);
    schedule->gap_count = 0;
    
    /* Day boundaries */
    TimeSlot wake = {WAKE_HOUR, WAKE_MIN};
    TimeSlot sleep = {SLEEP_HOUR, SLEEP_MIN};
    
    TimeSlot current = wake;
    
    for (int i = 0; i < schedule->task_count; i++) {
        Task* task = &schedule->tasks[i];
        
        /* Check gap before this task */
        int gap_mins = time_to_minutes(task->start_time) - time_to_minutes(current);
        
        if (gap_mins >= DEEP_WORK_MIN_MINUTES) {
            ScheduleGap gap;
            gap.start = current;
            gap.end = task->start_time;
            gap.duration_mins = gap_mins;
            schedule->gaps[schedule->gap_count++] = gap;
        }
        
        /* Move current to end of this task */
        current = task->end_time;
    }
    
    /* Check gap after last task until sleep */
    int final_gap = time_to_minutes(sleep) - time_to_minutes(current);
    if (final_gap >= DEEP_WORK_MIN_MINUTES) {
        ScheduleGap gap;
        gap.start = current;
        gap.end = sleep;
        gap.duration_mins = final_gap;
        schedule->gaps[schedule->gap_count++] = gap;
    }
    
    return schedule->gap_count;
}

int get_deep_work_gaps(DailySchedule* schedule, ScheduleGap** out_gaps) {
    int count = analyze_gaps(schedule);
    *out_gaps = schedule->gaps;
    return count;
}

void print_gaps(DailySchedule* schedule) {
    printf("\n=== Deep Work Gaps (>%d mins) ===\n", DEEP_WORK_MIN_MINUTES);
    
    if (schedule->gap_count == 0) {
        printf("No deep work gaps found.\n");
        return;
    }
    
    for (int i = 0; i < schedule->gap_count; i++) {
        ScheduleGap* gap = &schedule->gaps[i];
        printf("Gap %d: %02d:%02d - %02d:%02d (%d mins)\n",
               i + 1,
               gap->start.hour, gap->start.minute,
               gap->end.hour, gap->end.minute,
               gap->duration_mins);
    }
}

/* ============================================
 * PRIORITY QUEUE (MIN-HEAP)
 * ============================================ */

/* Compare by deadline first, then by credits (higher credits = higher priority) */
static int compare_reports(LabReport* a, LabReport* b) {
    if (a->deadline != b->deadline) {
        return (a->deadline < b->deadline) ? -1 : 1;
    }
    /* Same deadline: higher credits = higher priority (comes first) */
    return b->credits - a->credits;
}

void pq_heapify_up(PriorityQueue* pq, int index) {
    while (index > 0) {
        int parent = (index - 1) / 2;
        if (compare_reports(&pq->reports[index], &pq->reports[parent]) < 0) {
            /* Swap */
            LabReport temp = pq->reports[index];
            pq->reports[index] = pq->reports[parent];
            pq->reports[parent] = temp;
            index = parent;
        } else {
            break;
        }
    }
}

void pq_heapify_down(PriorityQueue* pq, int index) {
    while (1) {
        int smallest = index;
        int left = 2 * index + 1;
        int right = 2 * index + 2;
        
        if (left < pq->size && 
            compare_reports(&pq->reports[left], &pq->reports[smallest]) < 0) {
            smallest = left;
        }
        if (right < pq->size && 
            compare_reports(&pq->reports[right], &pq->reports[smallest]) < 0) {
            smallest = right;
        }
        
        if (smallest != index) {
            LabReport temp = pq->reports[index];
            pq->reports[index] = pq->reports[smallest];
            pq->reports[smallest] = temp;
            index = smallest;
        } else {
            break;
        }
    }
}

void pq_insert(PriorityQueue* pq, LabReport report) {
    if (pq->size >= pq->capacity) {
        fprintf(stderr, "Error: Priority queue is full\n");
        return;
    }
    
    report.id = pq->size + 1;
    pq->reports[pq->size] = report;
    pq_heapify_up(pq, pq->size);
    pq->size++;
}

LabReport pq_extract_min(PriorityQueue* pq) {
    LabReport empty = {0};
    if (pq->size == 0) {
        fprintf(stderr, "Error: Priority queue is empty\n");
        return empty;
    }
    
    LabReport min = pq->reports[0];
    pq->reports[0] = pq->reports[pq->size - 1];
    pq->size--;
    pq_heapify_down(pq, 0);
    
    return min;
}

LabReport pq_peek(PriorityQueue* pq) {
    LabReport empty = {0};
    if (pq->size == 0) {
        return empty;
    }
    return pq->reports[0];
}

bool pq_is_empty(PriorityQueue* pq) {
    return pq->size == 0;
}

/* ============================================
 * BINARY FILE I/O
 * ============================================ */

int save_schedule(DailySchedule* schedule, const char* filename) {
    FILE* fp = fopen(filename, "wb");
    if (!fp) {
        fprintf(stderr, "Error: Cannot open %s for writing\n", filename);
        return -1;
    }
    
    /* Write metadata */
    fwrite(&schedule->task_count, sizeof(int), 1, fp);
    fwrite(&schedule->gap_count, sizeof(int), 1, fp);
    
    /* Write tasks */
    fwrite(schedule->tasks, sizeof(Task), schedule->task_count, fp);
    
    /* Write gaps */
    fwrite(schedule->gaps, sizeof(ScheduleGap), schedule->gap_count, fp);
    
    fclose(fp);
    printf("Schedule saved to %s\n", filename);
    return 0;
}

DailySchedule* load_schedule(const char* filename) {
    FILE* fp = fopen(filename, "rb");
    if (!fp) {
        fprintf(stderr, "Error: Cannot open %s for reading\n", filename);
        return NULL;
    }
    
    int task_count, gap_count;
    fread(&task_count, sizeof(int), 1, fp);
    fread(&gap_count, sizeof(int), 1, fp);
    
    DailySchedule* schedule = schedule_create(MAX_TASKS);
    if (!schedule) {
        fclose(fp);
        return NULL;
    }
    
    fread(schedule->tasks, sizeof(Task), task_count, fp);
    schedule->task_count = task_count;
    
    fread(schedule->gaps, sizeof(ScheduleGap), gap_count, fp);
    schedule->gap_count = gap_count;
    
    fclose(fp);
    printf("Schedule loaded from %s\n", filename);
    return schedule;
}

int save_lab_queue(PriorityQueue* pq, const char* filename) {
    FILE* fp = fopen(filename, "wb");
    if (!fp) {
        fprintf(stderr, "Error: Cannot open %s for writing\n", filename);
        return -1;
    }
    
    fwrite(&pq->size, sizeof(int), 1, fp);
    fwrite(pq->reports, sizeof(LabReport), pq->size, fp);
    
    fclose(fp);
    return 0;
}

PriorityQueue* load_lab_queue(const char* filename) {
    FILE* fp = fopen(filename, "rb");
    if (!fp) {
        return NULL;
    }
    
    int size;
    fread(&size, sizeof(int), 1, fp);
    
    PriorityQueue* pq = pq_create(MAX_TASKS);
    if (!pq) {
        fclose(fp);
        return NULL;
    }
    
    fread(pq->reports, sizeof(LabReport), size, fp);
    pq->size = size;
    
    fclose(fp);
    return pq;
}

/* ============================================
 * PRINT FUNCTIONS
 * ============================================ */

void print_task(Task* task) {
    printf("[%d] %s (%s) - %02d:%02d to %02d:%02d (%d mins) P%d %s\n",
           task->id,
           task->title,
           task->subject,
           task->start_time.hour, task->start_time.minute,
           task->end_time.hour, task->end_time.minute,
           task->duration_mins,
           task->priority,
           task->is_deep_work ? "[DEEP]" : "");
}

void print_schedule(DailySchedule* schedule) {
    printf("\n=== Daily Schedule ===\n");
    printf("Wake: %02d:%02d | Sleep: %02d:%02d\n\n", 
           WAKE_HOUR, WAKE_MIN, SLEEP_HOUR, SLEEP_MIN);
    
    if (schedule->task_count == 0) {
        printf("No tasks scheduled.\n");
        return;
    }
    
    schedule_sort_by_time(schedule);
    for (int i = 0; i < schedule->task_count; i++) {
        print_task(&schedule->tasks[i]);
    }
}

void print_lab_report(LabReport* report) {
    char deadline_str[26];
    struct tm* tm_info = localtime(&report->deadline);
    strftime(deadline_str, 26, "%Y-%m-%d %H:%M", tm_info);
    
    printf("[%d] %s (%s, %d cr) - Due: %s %s\n",
           report->id,
           report->title,
           report->subject,
           report->credits,
           deadline_str,
           report->completed ? "[DONE]" : "");
}

void print_queue(PriorityQueue* pq) {
    printf("\n=== Lab Report Queue (Priority Order) ===\n");
    
    if (pq->size == 0) {
        printf("No lab reports in queue.\n");
        return;
    }
    
    /* Create temp queue to peek all */
    for (int i = 0; i < pq->size; i++) {
        print_lab_report(&pq->reports[i]);
    }
}

/* ============================================
 * JSON OUTPUT (for Python integration)
 * ============================================ */

void print_gaps_json(DailySchedule* schedule) {
    printf("{\"gaps\": [");
    
    for (int i = 0; i < schedule->gap_count; i++) {
        ScheduleGap* gap = &schedule->gaps[i];
        printf("{\"start\": \"%02d:%02d\", \"end\": \"%02d:%02d\", \"duration_mins\": %d}",
               gap->start.hour, gap->start.minute,
               gap->end.hour, gap->end.minute,
               gap->duration_mins);
        if (i < schedule->gap_count - 1) printf(", ");
    }
    
    printf("], \"count\": %d}\n", schedule->gap_count);
}

void print_schedule_json(DailySchedule* schedule) {
    printf("{\"tasks\": [");
    
    for (int i = 0; i < schedule->task_count; i++) {
        Task* t = &schedule->tasks[i];
        printf("{\"id\": %d, \"title\": \"%s\", \"subject\": \"%s\", "
               "\"start\": \"%02d:%02d\", \"end\": \"%02d:%02d\", "
               "\"duration\": %d, \"priority\": %d, \"deep_work\": %s}",
               t->id, t->title, t->subject,
               t->start_time.hour, t->start_time.minute,
               t->end_time.hour, t->end_time.minute,
               t->duration_mins, t->priority,
               t->is_deep_work ? "true" : "false");
        if (i < schedule->task_count - 1) printf(", ");
    }
    
    printf("], \"count\": %d}\n", schedule->task_count);
}

void print_queue_json(PriorityQueue* pq) {
    printf("{\"reports\": [");
    
    for (int i = 0; i < pq->size; i++) {
        LabReport* r = &pq->reports[i];
        char deadline_str[26];
        struct tm* tm_info = localtime(&r->deadline);
        strftime(deadline_str, 26, "%Y-%m-%dT%H:%M:%S", tm_info);
        
        printf("{\"id\": %d, \"title\": \"%s\", \"subject\": \"%s\", "
               "\"deadline\": \"%s\", \"credits\": %d, \"completed\": %s}",
               r->id, r->title, r->subject, deadline_str, r->credits,
               r->completed ? "true" : "false");
        if (i < pq->size - 1) printf(", ");
    }
    
    printf("], \"count\": %d}\n", pq->size);
}

/* ============================================
 * MAIN - CLI Interface
 * ============================================ */

void print_usage(const char* program) {
    printf("\nPersonal Engineering OS - Scheduler Engine v1.0.1\n");
    printf("=================================================\n\n");
    printf("Usage: %s <command> [options]\n\n", program);
    printf("Commands:\n");
    printf("  --analyze-gaps        Find deep work gaps (>90 mins)\n");
    printf("  --list-schedule       Show current schedule\n");
    printf("  --list-queue          Show lab report queue\n");
    printf("  --add-task            Add a task (interactive)\n");
    printf("  --add-lab             Add a lab report (interactive)\n");
    printf("  --json                Output in JSON format\n");
    printf("  --help                Show this help\n");
    printf("\nExamples:\n");
    printf("  %s --analyze-gaps --json\n", program);
    printf("  %s --list-queue\n", program);
}

int main(int argc, char* argv[]) {
    bool json_output = false;
    
    /* Check for JSON flag */
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--json") == 0) {
            json_output = true;
        }
    }
    
    if (argc < 2) {
        print_usage(argv[0]);
        return 0;
    }
    
    /* Load or create schedule */
    DailySchedule* schedule = load_schedule(DATA_FILE);
    if (!schedule) {
        schedule = schedule_create(MAX_TASKS);
    }
    
    /* Load or create lab queue */
    PriorityQueue* pq = load_lab_queue("labs.dat");
    if (!pq) {
        pq = pq_create(MAX_TASKS);
    }
    
    /* Process commands */
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--help") == 0) {
            print_usage(argv[0]);
        }
        else if (strcmp(argv[i], "--analyze-gaps") == 0) {
            analyze_gaps(schedule);
            if (json_output) {
                print_gaps_json(schedule);
            } else {
                print_gaps(schedule);
            }
        }
        else if (strcmp(argv[i], "--list-schedule") == 0) {
            if (json_output) {
                print_schedule_json(schedule);
            } else {
                print_schedule(schedule);
            }
        }
        else if (strcmp(argv[i], "--list-queue") == 0) {
            if (json_output) {
                print_queue_json(pq);
            } else {
                print_queue(pq);
            }
        }
        else if (strcmp(argv[i], "--add-task") == 0) {
            Task task = {0};
            printf("Title: ");
            fgets(task.title, MAX_TITLE_LEN, stdin);
            task.title[strcspn(task.title, "\n")] = 0;
            
            printf("Subject (e.g., MATH101): ");
            fgets(task.subject, 20, stdin);
            task.subject[strcspn(task.subject, "\n")] = 0;
            
            printf("Start time (HH:MM): ");
            scanf("%d:%d", &task.start_time.hour, &task.start_time.minute);
            
            printf("Duration (mins): ");
            scanf("%d", &task.duration_mins);
            
            task.end_time = minutes_to_time(
                time_to_minutes(task.start_time) + task.duration_mins
            );
            
            printf("Priority (1-10): ");
            scanf("%d", &task.priority);
            
            task.is_deep_work = (task.duration_mins >= DEEP_WORK_MIN_MINUTES);
            
            schedule_add_task(schedule, task);
            save_schedule(schedule, DATA_FILE);
            printf("Task added!\n");
        }
        else if (strcmp(argv[i], "--add-lab") == 0) {
            LabReport report = {0};
            printf("Title: ");
            fgets(report.title, MAX_TITLE_LEN, stdin);
            report.title[strcspn(report.title, "\n")] = 0;
            
            printf("Subject (e.g., PHYS102): ");
            fgets(report.subject, 20, stdin);
            report.subject[strcspn(report.subject, "\n")] = 0;
            
            printf("Credits: ");
            scanf("%d", &report.credits);
            
            printf("Deadline (YYYY-MM-DD HH:MM): ");
            struct tm tm = {0};
            scanf("%d-%d-%d %d:%d", 
                  &tm.tm_year, &tm.tm_mon, &tm.tm_mday,
                  &tm.tm_hour, &tm.tm_min);
            tm.tm_year -= 1900;
            tm.tm_mon -= 1;
            report.deadline = mktime(&tm);
            
            pq_insert(pq, report);
            save_lab_queue(pq, "labs.dat");
            printf("Lab report added to queue!\n");
        }
    }
    
    /* Cleanup */
    schedule_destroy(schedule);
    pq_destroy(pq);
    
    return 0;
}
