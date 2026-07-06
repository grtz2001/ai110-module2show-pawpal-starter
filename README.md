# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Paste a sample of your app's CLI or Streamlit output here so a reader can see what a generated plan looks like:

========================================================
  TODAY'S SCHEDULE - Sunday, Jul 05
  Maria's pets - 4 tasks, 105 of 480 min used
========================================================
  TIME    PET       TASK                   DUR  PRIORITY
  ------  --------  --------------------  ----  --------
  08:00   Milo      Play / enrichment      20m  low
  08:30   Rex       Morning walk           30m  high
  09:00   Milo      Feed breakfast         10m  medium
  15:00   Rex       Vet appointment        45m  high
========================================================

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
# Paste your pytest output here
```

## 📐 Smarter Scheduling

All scheduling logic lives in `pawpal_system.py`. The table summarizes each
feature and the method that implements it; details follow below.

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `Scheduler.sort_by_priority()`, `Scheduler.sort_by_time()` | High→low priority (via `PRIORITY_RANK`), or by fixed time of day with flexible tasks last |
| Filtering | `Scheduler.filter_tasks()`, `Scheduler.filter_by_status()`, `Scheduler.tasks_for_pet()`, `Scheduler.tasks_due_on()` | By pet name (case-insensitive), completion status, or due-on-a-day; filters combine with AND |
| Conflict handling | `Scheduler.detect_conflicts()`, `Scheduler.find_overlaps()`, `Scheduler.conflict_warning()` | Overlapping time slots, detected on declared times *and* on the actual generated plan |
| Recurring tasks | `Task.is_due_on()`, `Task.next_occurrence()`, `Scheduler.complete_task()` | Daily/weekly recurrence with per-day completion; completing a task spawns the next occurrence |

### Sorting behavior

- **`Scheduler.sort_by_priority()`** returns every task across all pets ordered
  high → low priority. Priority strings are mapped through `PRIORITY_RANK`
  (`high=0, medium=1, low=2`) because sorting the strings directly would give
  the wrong (alphabetical) order. The sort is stable, so equal-priority tasks
  keep their original order.
- **`Scheduler.sort_by_time()`** orders tasks by their fixed time of day,
  earliest first. Flexible tasks (`time is None`) have no anchored slot, so they
  sort after all fixed-time tasks.

### Filtering behavior

- **`Scheduler.filter_tasks(pet_name, completed, day)`** is the general filter:
  keep tasks by pet name (case-insensitive), by completion status, or both. The
  filters combine with AND, and completion is judged per-day when a `day` is
  given, otherwise by the permanent `completed` flag.
- **`Scheduler.filter_by_status(completed, day)`** filters all tasks by
  completion status alone.
- **`Scheduler.tasks_for_pet(pet)`** returns just one pet's tasks.
- **`Scheduler.tasks_due_on(day)`** returns the still-to-do tasks that should
  happen on a given day (recurrence-aware and skipping ones already done).

### Conflict detection logic

- **`Scheduler.detect_conflicts(day)`** finds pairs of *fixed-time* tasks whose
  declared slots overlap, before any planning happens. It sorts anchored tasks
  by time and, for each, compares against later tasks until one starts after the
  current one ends (the sort lets it stop early). Returns `(task_a, task_b)`
  pairs.
- **`Scheduler.find_overlaps(plan)`** inspects the *actual* generated plan
  (`self.last_plan` by default), so it catches any two placed tasks sharing
  clock time — including flexible tasks and cross-pet clashes. Returns
  `(item_a, item_b, same_pet)` tuples, where `same_pet` flags a hard, physically
  impossible clash for one pet versus a cross-pet collision.
- **`Scheduler.conflict_warning()`** is a crash-proof wrapper over
  `find_overlaps()` that returns a human-readable one-line warning (or an empty
  string), for the UI to display.

### Recurring task logic

- **`Task.is_due_on(day)`** decides whether a task appears on a given day. A task
  pinned to a `due_date` isn't due before it; daily tasks are due every day and
  weekly tasks only on their `due_weekday`. Completion is tracked per-day in
  `completed_on`, so recurring tasks reset automatically each new day.
- **`Task.next_occurrence(on)`** returns a fresh copy of a recurring task with a
  reset completion history and its `due_date` advanced by one interval
  (`on + 1 day` for daily, `+ 1 week` for weekly). Non-recurring tasks return
  `None`.
- **`Scheduler.complete_task(task, on)`** ties it together: it retires the
  finished occurrence and, for a daily/weekly task, attaches the next occurrence
  to the same pet so the schedule rolls forward automatically.

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
