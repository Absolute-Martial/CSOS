/*
 * Personal Engineering OS - Scheduler Engine
 * scheduler.h - Header file
 * COMP 102 aligned: structs, memory management, binary I/O
 */

#ifndef SCHEDULER_H
#define SCHEDULER_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <stdbool.h>

/* ============================================
 * CONSTANTS
 * ============================================ */

#define MAX_TITLE_LEN 200
#define MAX_TASKS 100
#define DEEP_WORK_MIN_MINUTES 90
#define WAKE_HOUR 4
#define WAKE_MIN 30
#define SLEEP_HOUR 22
#define SLEEP_MIN 30
#define DATA_FILE "schedule.dat"

/* ============================================
 * STRUCTURES
 * ============================================ */

/* Time slot representation */
typedef struct {
    int hour;
    int minute;
} TimeSlot;

/* Task structure for schedule */
typedef struct {
    int id;
    char title[MAX_TITLE_LEN];
    char subject[20];
    int priority;           /* 1-10, higher = more important */
    int duration_mins;
    TimeSlot start_time;
    TimeSlot end_time;
    bool is_deep_work;
    bool completed;
} Task;

/* Gap in schedule (potential deep work) */
typedef struct {
    TimeSlot start;
    TimeSlot end;
    int duration_mins;
} ScheduleGap;

/* Lab report for priority queue */
typedef struct {
    int id;
    char title[MAX_TITLE_LEN];
    char subject[20];
    time_t deadline;
    int credits;            /* Subject credits for priority */
    bool completed;
} LabReport;

/* Priority queue (min-heap by deadline & credits) */
typedef struct {
    LabReport* reports;
    int size;
    int capacity;
} PriorityQueue;

/* Daily schedule container */
typedef struct {
    Task* tasks;
    int task_count;
    int capacity;
    ScheduleGap* gaps;
    int gap_count;
} DailySchedule;

/* ============================================
 * FUNCTION PROTOTYPES
 * ============================================ */

/* Memory management */
DailySchedule* schedule_create(int capacity);
void schedule_destroy(DailySchedule* schedule);
PriorityQueue* pq_create(int capacity);
void pq_destroy(PriorityQueue* pq);

/* Schedule operations */
int schedule_add_task(DailySchedule* schedule, Task task);
int schedule_remove_task(DailySchedule* schedule, int task_id);
void schedule_sort_by_time(DailySchedule* schedule);

/* Deep work gap analysis */
int analyze_gaps(DailySchedule* schedule);
void print_gaps(DailySchedule* schedule);
int get_deep_work_gaps(DailySchedule* schedule, ScheduleGap** out_gaps);

/* Priority queue (min-heap) */
void pq_insert(PriorityQueue* pq, LabReport report);
LabReport pq_extract_min(PriorityQueue* pq);
LabReport pq_peek(PriorityQueue* pq);
bool pq_is_empty(PriorityQueue* pq);
void pq_heapify_up(PriorityQueue* pq, int index);
void pq_heapify_down(PriorityQueue* pq, int index);

/* Binary file I/O */
int save_schedule(DailySchedule* schedule, const char* filename);
DailySchedule* load_schedule(const char* filename);
int save_lab_queue(PriorityQueue* pq, const char* filename);
PriorityQueue* load_lab_queue(const char* filename);

/* Utility functions */
int time_to_minutes(TimeSlot t);
TimeSlot minutes_to_time(int minutes);
int compare_time(TimeSlot a, TimeSlot b);
void print_task(Task* task);
void print_schedule(DailySchedule* schedule);
void print_lab_report(LabReport* report);
void print_queue(PriorityQueue* pq);

/* JSON output for Python integration */
void print_gaps_json(DailySchedule* schedule);
void print_schedule_json(DailySchedule* schedule);
void print_queue_json(PriorityQueue* pq);

#endif /* SCHEDULER_H */
