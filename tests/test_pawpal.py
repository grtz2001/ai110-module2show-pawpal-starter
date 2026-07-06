"""Simple tests for the PawPal+ logic layer."""

from datetime import date, time

from pawpal_system import Owner, Pet, Scheduler, Task


def test_mark_complete_changes_status():
    """Calling mark_complete() should flip the task's status to done."""
    task = Task(description="Walk the dog")
    assert task.completed is False

    task.mark_complete()

    assert task.completed is True


def test_add_task_increases_pet_task_count():
    """Adding a task to a Pet should increase that pet's task count."""
    pet = Pet(name="Rex", species="dog")
    assert len(pet.get_tasks()) == 0

    pet.add_task(Task(description="Feed breakfast"))

    assert len(pet.get_tasks()) == 1


# --- #1: weekly tasks only appear on their weekday --------------------------

MONDAY = date(2026, 7, 6)     # a Monday
TUESDAY = date(2026, 7, 7)


def _scheduler_with(*tasks, available_minutes=480):
    """Build an Owner with one pet holding ``tasks`` and a Scheduler for it."""
    pet = Pet(name="Rex", species="dog")
    for task in tasks:
        pet.add_task(task)
    owner = Owner(name="Jordan", email="j@example.com")
    owner.add_pet(pet)
    return Scheduler(owner, available_minutes=available_minutes)


def test_weekly_task_only_scheduled_on_its_weekday():
    """A weekly task due Monday appears Monday but not Tuesday."""
    task = Task(description="Weekly grooming", frequency="weekly", due_weekday=0)
    scheduler = _scheduler_with(task)

    monday_plan = scheduler.generate_daily_plan(MONDAY)
    tuesday_plan = scheduler.generate_daily_plan(TUESDAY)

    assert [i.task for i in monday_plan] == [task]
    assert tuesday_plan == []


def test_daily_task_scheduled_every_day():
    """A daily task shows up regardless of weekday."""
    task = Task(description="Morning walk", frequency="daily")
    scheduler = _scheduler_with(task)

    assert len(scheduler.generate_daily_plan(MONDAY)) == 1
    assert len(scheduler.generate_daily_plan(TUESDAY)) == 1


# --- #2: per-day completion resets for recurring tasks ----------------------

def test_marking_done_for_a_day_skips_only_that_day():
    """Completing a task for one day still schedules it the next day."""
    task = Task(description="Feed breakfast", frequency="daily")
    scheduler = _scheduler_with(task)

    task.mark_complete(MONDAY)

    assert scheduler.generate_daily_plan(MONDAY) == []          # done today
    assert len(scheduler.generate_daily_plan(TUESDAY)) == 1     # due again


def test_permanent_complete_skips_every_day():
    """mark_complete() with no day removes the task from all plans."""
    task = Task(description="One-off errand")
    scheduler = _scheduler_with(task)

    task.mark_complete()

    assert scheduler.generate_daily_plan(MONDAY) == []
    assert scheduler.generate_daily_plan(TUESDAY) == []


# --- #4: time windows for flexible tasks ------------------------------------

def test_flexible_task_respects_earliest_time():
    """A task with an earliest time is placed no earlier than that time."""
    task = Task(description="Evening walk", earliest=time(18, 0))
    scheduler = _scheduler_with(task)

    plan = scheduler.generate_daily_plan(MONDAY)

    assert plan[0].start_time >= time(18, 0)


def test_flexible_task_skipped_if_it_cannot_finish_by_latest():
    """A task that can't fit before its latest time is left out."""
    task = Task(description="Quick meds", duration_minutes=30, latest=time(8, 20))
    scheduler = _scheduler_with(task)

    # Day starts 08:00; a 30-min task can't finish by 08:20, so it's skipped.
    assert scheduler.generate_daily_plan(MONDAY) == []


# --- sorting tasks by time --------------------------------------------------

def test_sort_by_time_orders_anchored_and_puts_flexible_last():
    """Fixed-time tasks come out earliest-first; flexible tasks sort last."""
    flexible = Task(description="Play")
    late = Task(description="Vet", time=time(15, 0))
    early = Task(description="Walk", time=time(8, 0))
    scheduler = _scheduler_with(flexible, late, early)

    ordered = scheduler.sort_by_time()

    assert ordered == [early, late, flexible]


# --- filtering by pet / status ----------------------------------------------

def test_tasks_for_pet_returns_only_that_pets_tasks():
    """tasks_for_pet filters the plan down to a single pet."""
    rex = Pet(name="Rex", species="dog")
    milo = Pet(name="Milo", species="cat")
    rex_task = Task(description="Walk Rex")
    milo_task = Task(description="Feed Milo")
    rex.add_task(rex_task)
    milo.add_task(milo_task)
    owner = Owner(name="Jordan", email="j@example.com")
    owner.add_pet(rex)
    owner.add_pet(milo)
    scheduler = Scheduler(owner, available_minutes=480)

    assert scheduler.tasks_for_pet(rex) == [rex_task]
    assert scheduler.tasks_for_pet(milo) == [milo_task]


def test_filter_by_status_separates_done_and_pending():
    """filter_by_status splits tasks by completion (per-day when given a day)."""
    done_today = Task(description="Morning walk")
    pending = Task(description="Evening walk")
    scheduler = _scheduler_with(done_today, pending)

    done_today.mark_complete(MONDAY)

    assert scheduler.filter_by_status(completed=True, day=MONDAY) == [done_today]
    assert scheduler.filter_by_status(completed=False, day=MONDAY) == [pending]
    # No day supplied → per-day completion doesn't count as permanently done.
    assert scheduler.filter_by_status(completed=False) == [done_today, pending]


# --- basic conflict detection -----------------------------------------------

def test_detect_conflicts_finds_overlapping_fixed_time_tasks():
    """Two anchored tasks whose slots overlap are reported as a conflict."""
    vet = Task(description="Vet", time=time(15, 0), duration_minutes=45)
    grooming = Task(description="Grooming", time=time(15, 30), duration_minutes=30)
    scheduler = _scheduler_with(vet, grooming)

    conflicts = scheduler.detect_conflicts(MONDAY)

    assert conflicts == [(vet, grooming)]  # earlier task first


def test_detect_conflicts_ignores_back_to_back_tasks():
    """Tasks that touch but don't overlap are not a conflict."""
    walk = Task(description="Walk", time=time(8, 0), duration_minutes=30)
    feed = Task(description="Feed", time=time(8, 30), duration_minutes=15)
    scheduler = _scheduler_with(walk, feed)

    assert scheduler.detect_conflicts(MONDAY) == []
