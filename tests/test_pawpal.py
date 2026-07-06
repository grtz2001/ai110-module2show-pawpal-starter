"""Simple tests for the PawPal+ logic layer."""

from datetime import date, time

from pawpal_system import Owner, Pet, PlannedItem, Scheduler, Task


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


def _two_pet_scheduler():
    """Owner with Rex (walk done today, feed pending) and Milo (one pending)."""
    rex = Pet(name="Rex", species="dog")
    milo = Pet(name="Milo", species="cat")
    rex_walk = Task(description="Walk Rex")
    rex_feed = Task(description="Feed Rex")
    milo_feed = Task(description="Feed Milo")
    rex.add_task(rex_walk)
    rex.add_task(rex_feed)
    milo.add_task(milo_feed)
    owner = Owner(name="Jordan", email="j@example.com")
    owner.add_pet(rex)
    owner.add_pet(milo)
    scheduler = Scheduler(owner, available_minutes=480)
    return scheduler, rex_walk, rex_feed, milo_feed


def test_filter_tasks_by_pet_name_is_case_insensitive():
    """Filtering by pet name returns only that pet's tasks, ignoring case."""
    scheduler, rex_walk, rex_feed, _ = _two_pet_scheduler()

    assert scheduler.filter_tasks(pet_name="rex") == [rex_walk, rex_feed]


def test_filter_tasks_by_status():
    """Filtering by completion status uses per-day status when a day is given."""
    scheduler, rex_walk, rex_feed, milo_feed = _two_pet_scheduler()

    rex_walk.mark_complete(MONDAY)

    assert scheduler.filter_tasks(completed=True, day=MONDAY) == [rex_walk]
    assert scheduler.filter_tasks(completed=False, day=MONDAY) == [rex_feed, milo_feed]


def test_filter_tasks_by_pet_and_status_combined():
    """Both filters combine with AND."""
    scheduler, rex_walk, rex_feed, _ = _two_pet_scheduler()

    rex_walk.mark_complete(MONDAY)

    assert scheduler.filter_tasks(pet_name="Rex", completed=False, day=MONDAY) == [rex_feed]


def test_filter_tasks_no_filters_returns_everything():
    """With no filters, every task across all pets is returned."""
    scheduler, rex_walk, rex_feed, milo_feed = _two_pet_scheduler()

    assert scheduler.filter_tasks() == [rex_walk, rex_feed, milo_feed]


# --- auto-recurrence: completing a task spawns its next occurrence ----------

def test_completing_daily_task_spawns_next_occurrence():
    """Completing a daily task retires it and adds a fresh instance to the pet."""
    task = Task(description="Morning walk", frequency="daily")
    scheduler = _scheduler_with(task)
    pet = scheduler.owner.pets[0]

    upcoming = scheduler.complete_task(task, on=MONDAY)

    assert len(pet.tasks) == 2                 # original + next occurrence
    assert task.completed is True              # old occurrence retired
    assert upcoming is not None
    assert upcoming.completed is False         # new occurrence is fresh
    assert upcoming.description == "Morning walk"
    assert upcoming.due_date == TUESDAY        # daily -> completion day + 1 day


def test_daily_next_occurrence_due_date_uses_timedelta():
    """A daily task completed late in the month rolls over the month boundary."""
    task = Task(description="Nightly meds", frequency="daily")
    scheduler = _scheduler_with(task)

    end_of_month = date(2026, 7, 31)
    upcoming = scheduler.complete_task(task, on=end_of_month)

    assert upcoming.due_date == date(2026, 8, 1)   # timedelta handles rollover


def test_weekly_next_occurrence_due_date_is_one_week_later():
    """A completed weekly task's next due_date is exactly seven days on."""
    task = Task(description="Weekly grooming", frequency="weekly", due_weekday=0)
    scheduler = _scheduler_with(task)

    upcoming = scheduler.complete_task(task, on=MONDAY)

    assert upcoming.due_date == date(2026, 7, 13)  # MONDAY + 1 week


def test_next_occurrence_is_not_rescheduled_same_day_but_is_next_day():
    """The spawned instance appears on the next day, not the day just completed."""
    task = Task(description="Feed breakfast", frequency="daily")
    scheduler = _scheduler_with(task)

    scheduler.complete_task(task, on=MONDAY)

    # Monday: original is done and the new instance is pre-marked done for Monday.
    assert scheduler.generate_daily_plan(MONDAY) == []
    # Tuesday: exactly one occurrence is due (the spawned instance, no duplicate).
    tuesday = scheduler.generate_daily_plan(TUESDAY)
    assert len(tuesday) == 1
    assert tuesday[0].task.description == "Feed breakfast"


def test_weekly_next_occurrence_keeps_its_weekday():
    """A completed weekly task rolls forward to the same weekday next week."""
    task = Task(description="Weekly grooming", frequency="weekly", due_weekday=0)
    scheduler = _scheduler_with(task)

    upcoming = scheduler.complete_task(task, on=MONDAY)

    assert upcoming.frequency == "weekly"
    assert upcoming.due_weekday == 0
    # Not due the day after (Tuesday); due again the following Monday.
    assert scheduler.generate_daily_plan(TUESDAY) == []
    next_monday = date(2026, 7, 13)
    assert len(scheduler.generate_daily_plan(next_monday)) == 1


def test_next_occurrence_has_independent_completion_history():
    """The clone must not share the original's completed_on set."""
    task = Task(description="Meds", frequency="daily")
    scheduler = _scheduler_with(task)

    upcoming = scheduler.complete_task(task, on=MONDAY)
    upcoming.completed_on.add(TUESDAY)

    assert TUESDAY not in task.completed_on    # sets are independent


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


# --- find_overlaps: same-time tasks in the generated plan -------------------

def test_find_overlaps_flags_same_pet_clash():
    """Two overlapping tasks for one pet are reported as a same-pet clash."""
    vet = Task(description="Vet", time=time(15, 0), duration_minutes=45)
    grooming = Task(description="Grooming", time=time(15, 30), duration_minutes=30)
    scheduler = _scheduler_with(vet, grooming)
    scheduler.generate_daily_plan(MONDAY)

    overlaps = scheduler.find_overlaps()

    assert len(overlaps) == 1
    earlier, later, same_pet = overlaps[0]
    assert earlier.task is vet and later.task is grooming
    assert same_pet is True


def test_find_overlaps_flags_cross_pet_clash():
    """Overlapping tasks belonging to different pets are flagged same_pet=False."""
    rex = Pet(name="Rex", species="dog")
    milo = Pet(name="Milo", species="cat")
    rex.add_task(Task(description="Walk Rex", time=time(8, 0), duration_minutes=30))
    milo.add_task(Task(description="Feed Milo", time=time(8, 15), duration_minutes=10))
    owner = Owner(name="Jordan", email="j@example.com")
    owner.add_pet(rex)
    owner.add_pet(milo)
    scheduler = Scheduler(owner, available_minutes=480)
    scheduler.generate_daily_plan(MONDAY)

    overlaps = scheduler.find_overlaps()

    assert len(overlaps) == 1
    _, _, same_pet = overlaps[0]
    assert same_pet is False


def test_find_overlaps_empty_when_nothing_collides():
    """A plan with only back-to-back tasks has no overlaps."""
    walk = Task(description="Walk", time=time(8, 0), duration_minutes=30)
    feed = Task(description="Feed", time=time(8, 30), duration_minutes=15)
    scheduler = _scheduler_with(walk, feed)
    scheduler.generate_daily_plan(MONDAY)

    assert scheduler.find_overlaps() == []


# --- lightweight, crash-proof conflict warning ------------------------------

def test_conflict_warning_empty_when_no_conflicts():
    """No conflicts -> empty string (nothing to show the user)."""
    walk = Task(description="Walk", time=time(8, 0), duration_minutes=30)
    scheduler = _scheduler_with(walk)
    scheduler.generate_daily_plan(MONDAY)

    assert scheduler.conflict_warning() == ""


def test_conflict_warning_describes_conflicts():
    """A conflict yields a human-readable warning string."""
    vet = Task(description="Vet", time=time(15, 0), duration_minutes=45)
    grooming = Task(description="Grooming", time=time(15, 30), duration_minutes=30)
    scheduler = _scheduler_with(vet, grooming)
    scheduler.generate_daily_plan(MONDAY)

    message = scheduler.conflict_warning()

    assert "conflict" in message.lower()
    assert "Vet" in message and "Grooming" in message


def test_conflict_warning_returns_message_instead_of_crashing():
    """A malformed plan entry is reported as a warning, not raised."""
    scheduler = _scheduler_with(Task(description="x"))
    pet = scheduler.owner.pets[0]
    # Two entries with no start_time would crash a naive check; conflict_warning
    # must swallow it and hand back a string.
    scheduler.last_plan = [
        PlannedItem(task=Task(description="A"), pet=pet, start_time=None),
        PlannedItem(task=Task(description="B"), pet=pet, start_time=None),
    ]

    message = scheduler.conflict_warning()

    assert isinstance(message, str)
    assert message.startswith("⚠️")
