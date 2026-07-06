"""PawPal+ logic layer.

Four core classes for the pet care planner:

* Task      - a single activity: description, time, frequency, completion status.
* Pet       - pet details plus the list of tasks that pet needs.
* Owner     - manages multiple pets and gives access to all of their tasks.
* Scheduler - the "brain" that retrieves, organizes, and manages tasks across pets.

A Task with a fixed ``time`` is an anchored commitment (like a vet visit); a Task
with ``time = None`` is flexible and the Scheduler places it in a free slot.

See diagrams/uml.mmd for the matching UML diagram.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, time, timedelta

# Priority order for sorting tasks. Sorting the strings directly would give
# alphabetical order (high < low < medium), which is wrong, so map to a rank.
PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}

# Bounds of the planning window. Flexible tasks are placed between these hours,
# fitting around any tasks that are anchored to a fixed time during the day.
DAY_START = time(8, 0)
DAY_END = time(20, 0)


def _minutes(t: time) -> int:
    """Convert a clock time into minutes-since-midnight for easy arithmetic."""
    return t.hour * 60 + t.minute


def _clock(total_minutes: int) -> time:
    """Convert minutes-since-midnight back into a clock time (clamped to a day)."""
    total_minutes = max(0, min(total_minutes, 23 * 60 + 59))
    return time(hour=total_minutes // 60, minute=total_minutes % 60)


def _next_free_slot(start: int, duration: int, blocked: list) -> int:
    """Earliest start time (>= ``start``) where ``duration`` fits without overlap.

    ``blocked`` is a list of (start_minute, end_minute) intervals already taken.
    We scan them in order, jumping the cursor past any interval it collides with.
    """
    for block_start, block_end in sorted(blocked):
        if start + duration <= block_start:
            break            # the task ends before this block begins — it fits
        if start < block_end:
            start = block_end  # overlap: push the cursor to the end of the block
    return start


@dataclass
class Task:
    """A single pet-care activity.

    The four core attributes from the design are ``description``, ``time``,
    ``frequency``, and ``completed``. ``duration_minutes`` and ``priority`` are
    extra hints the Scheduler uses to decide how long a task takes and what
    order to place tasks in.
    """

    description: str
    time: time = None          # fixed time of day, or None for a flexible task
    frequency: str = "daily"   # "daily" | "weekly"
    completed: bool = False     # True = permanently done (e.g. a one-off errand)
    duration_minutes: int = 15
    priority: str = "medium"   # "low" | "medium" | "high"
    # For weekly tasks: which weekday it recurs on (0 = Monday .. 6 = Sunday,
    # matching date.weekday()). None means "any day" (falls back to daily-like).
    due_weekday: int = None
    # Optional time-of-day window for a flexible task: the Scheduler will only
    # place it at or after ``earliest`` and finishing by ``latest``.
    earliest: time = None
    latest: time = None
    # The specific date this occurrence is scheduled for. None means the task
    # recurs by frequency/weekday alone (not pinned to a single date). When a
    # task is completed, complete_task() spawns a fresh copy whose due_date is
    # advanced by one interval (see next_occurrence).
    due_date: date = None
    # Dates this task has been completed on. Recurring tasks reset each day
    # because a new day is simply a date not yet in this set.
    completed_on: set = field(default_factory=set)

    def mark_complete(self, day=None) -> None:
        """Mark this task as done.

        With no ``day`` it is marked *permanently* done (for one-off tasks).
        With a ``day`` it is marked done for that date only, so a daily or
        weekly task becomes due again on the next occurrence.
        """
        if day is None:
            self.completed = True
        else:
            self.completed_on.add(day)

    def is_due_on(self, day: date) -> bool:
        """Whether this task should appear on ``day``.

        If the task is pinned to a ``due_date`` (as spawned occurrences are), it
        is not due before that date; on/after it, daily tasks are due every day
        and weekly tasks only on their weekday. With no ``due_date`` the task
        falls back to plain frequency/weekday recurrence.
        """
        if self.due_date is not None:
            if day < self.due_date:
                return False
            if self.frequency == "weekly" and self.due_weekday is not None:
                return day.weekday() == self.due_weekday
            return True
        if self.frequency == "weekly":
            return self.due_weekday is None or day.weekday() == self.due_weekday
        return True  # daily (the default) is due every day

    def is_done_on(self, day: date) -> bool:
        """Whether this task is already completed for ``day``.

        A permanently completed task counts as done every day; otherwise
        completion is tracked per-date so recurring tasks reset automatically.
        """
        return self.completed or day in self.completed_on

    def next_occurrence(self, on: date):
        """Return a fresh copy of this recurring task, due after ``on``.

        ``on`` is the date the current occurrence was completed. A daily task's
        next ``due_date`` is ``on + 1 day``; a weekly task's is ``on + 1 week``
        (which lands on the same weekday). The copy keeps the same description,
        time-of-day, duration, priority, frequency and weekday, but its
        completion history is reset. Returns ``None`` for a non-recurring task.
        """
        if self.frequency == "daily":
            step = timedelta(days=1)
        elif self.frequency == "weekly":
            step = timedelta(weeks=1)
        else:
            return None
        # replace() copies every field; override completion state (a fresh set,
        # not a shared reference) and pin the new occurrence to its next date.
        return replace(self, completed=False, completed_on=set(), due_date=on + step)

    def edit(
        self,
        description=None,
        time=None,
        frequency=None,
        duration_minutes=None,
        priority=None,
        due_weekday=None,
        earliest=None,
        latest=None,
    ) -> None:
        """Update this task's details. Only the fields you pass are changed."""
        if description is not None:
            self.description = description
        if time is not None:
            self.time = time
        if frequency is not None:
            self.frequency = frequency
        if duration_minutes is not None:
            self.duration_minutes = duration_minutes
        if priority is not None:
            self.priority = priority
        if due_weekday is not None:
            self.due_weekday = due_weekday
        if earliest is not None:
            self.earliest = earliest
        if latest is not None:
            self.latest = latest


@dataclass
class Pet:
    """The animal being cared for; holds its info and the tasks it needs."""

    name: str
    species: str
    breed: str = ""
    age: int = 0
    weight: float = 0.0
    notes: str = ""
    tasks: list = field(default_factory=list)   # list[Task]

    def edit_info(self, name=None, breed=None, weight=None, notes=None) -> None:
        """Update this pet's details. Only the fields you pass are changed."""
        if name is not None:
            self.name = name
        if breed is not None:
            self.breed = breed
        if weight is not None:
            self.weight = weight
        if notes is not None:
            self.notes = notes

    def add_task(self, task: Task) -> None:
        """Attach a care task to this pet."""
        self.tasks.append(task)

    def get_tasks(self) -> list:
        """Return this pet's tasks."""
        return self.tasks


@dataclass
class Owner:
    """The person using the app; manages multiple pets and their tasks."""

    name: str
    email: str
    pets: list = field(default_factory=list)          # list[Pet]
    preferences: dict = field(default_factory=dict)
    shared_with: list = field(default_factory=list)   # people the plan is shared with

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner."""
        self.pets.append(pet)

    def get_all_tasks(self) -> list:
        """Return every task across all of this owner's pets, flattened.

        This is the single accessor the Scheduler uses to reach pet data:
        rather than the Scheduler digging into each pet itself, the Owner owns
        the "which pets exist" knowledge and hands back all of their tasks.
        """
        all_tasks = []
        for pet in self.pets:
            all_tasks.extend(pet.tasks)
        return all_tasks

    def share_with(self, person: str) -> None:
        """Share this owner's care plan with someone (no duplicates)."""
        if person not in self.shared_with:
            self.shared_with.append(person)


@dataclass
class PlannedItem:
    """One entry in a generated plan: a task placed at a start time, and whose pet it is."""

    task: Task
    pet: Pet
    start_time: time


class Scheduler:
    """The brain; retrieves, organizes, and plans tasks across all of an owner's pets."""

    def __init__(self, owner: Owner, available_minutes: int):
        """Create a scheduler for one owner with a daily care-time budget."""
        self.owner = owner                       # all tasks are reached through here
        self.available_minutes = available_minutes
        # Remember the most recent plan so explain_plan() can describe it.
        self.last_day = None
        self.last_plan = []

    def _pet_by_task(self) -> dict:
        """Map each task's identity to the pet that owns it (for labelling)."""
        return {id(task): pet for pet in self.owner.pets for task in pet.tasks}

    def sort_by_priority(self) -> list:
        """Return every task across all pets, ordered high -> low priority.

        Uses a stable sort, so tasks of equal priority keep their original order.
        """
        return sorted(
            self.owner.get_all_tasks(),
            key=lambda task: PRIORITY_RANK.get(task.priority, len(PRIORITY_RANK)),
        )

    def sort_by_time(self) -> list:
        """Return every task ordered by its fixed time of day.

        Flexible tasks (``time is None``) have no fixed slot, so they sort after
        all anchored tasks. Anchored tasks are ordered earliest-first.
        """
        return sorted(
            self.owner.get_all_tasks(),
            key=lambda task: (task.time is None, _minutes(task.time) if task.time else 0),
        )

    def tasks_for_pet(self, pet: Pet) -> list:
        """Return just the tasks belonging to ``pet`` (filter by pet)."""
        return list(pet.tasks)

    def filter_by_status(self, completed: bool, day: date = None) -> list:
        """Return tasks across all pets matching a completion status.

        Without ``day`` this uses the permanent ``completed`` flag; with a
        ``day`` it uses that day's status, so recurring tasks are judged per-day.
        """
        def is_done(task):
            return task.is_done_on(day) if day is not None else task.completed

        return [task for task in self.owner.get_all_tasks() if is_done(task) == completed]

    def filter_tasks(self, pet_name: str = None, completed: bool = None,
                     day: date = None) -> list:
        """Return tasks across all pets, filtered by pet name and/or status.

        - ``pet_name``: keep only tasks of the pet with this name
          (case-insensitive). ``None`` means any pet.
        - ``completed``: keep only tasks with this completion status. ``None``
          means any status; judged per-day when ``day`` is given, otherwise by
          the permanent ``completed`` flag.

        Both filters are optional and combine with AND, so pass just one to
        filter by completion status or pet name alone.
        """
        wanted_name = pet_name.lower() if pet_name is not None else None

        results = []
        for pet in self.owner.pets:
            if wanted_name is not None and pet.name.lower() != wanted_name:
                continue
            for task in pet.tasks:
                if completed is not None:
                    is_done = task.is_done_on(day) if day is not None else task.completed
                    if is_done != completed:
                        continue
                results.append(task)
        return results

    def complete_task(self, task: Task, on: date = None):
        """Mark ``task`` done and roll a recurring task forward to next time.

        The finished occurrence is retired (marked permanently complete so it is
        never scheduled again). For a daily or weekly task, a fresh instance is
        created via ``Task.next_occurrence`` and attached to the same pet. The
        new instance's ``due_date`` is set to the next occurrence (``on + 1 day``
        for daily, ``+ 1 week`` for weekly), so it does not re-appear on the day
        just completed and becomes due on that next date.

        Returns the newly created Task, or ``None`` if the task does not recur
        (or isn't owned by any of this owner's pets).
        """
        if on is None:
            on = date.today()

        # Find the owning pet by identity (not equality — dataclasses compare by
        # value, and two tasks could look identical).
        pet = next(
            (p for p in self.owner.pets if any(t is task for t in p.tasks)),
            None,
        )

        task.mark_complete()  # retire this occurrence permanently

        upcoming = task.next_occurrence(on)
        if upcoming is None or pet is None:
            return None

        pet.add_task(upcoming)
        return upcoming

    def tasks_due_on(self, day: date) -> list:
        """Return the still-to-do tasks that should happen on ``day``.

        Recurring-aware: honours each task's frequency and per-day completion.
        """
        return [
            task
            for task in self.owner.get_all_tasks()
            if task.is_due_on(day) and not task.is_done_on(day)
        ]

    def detect_conflicts(self, day: date = None) -> list:
        """Find pairs of fixed-time tasks whose time slots overlap.

        Only anchored tasks (those with a fixed ``time``) can conflict — flexible
        tasks are placed into free gaps and never overlap. When ``day`` is given,
        only tasks due (and not yet done) on that day are considered.

        Returns a list of ``(task_a, task_b)`` pairs, earliest task first.
        """
        anchored = [task for task in self.owner.get_all_tasks() if task.time is not None]
        if day is not None:
            anchored = [
                task
                for task in anchored
                if task.is_due_on(day) and not task.is_done_on(day)
            ]
        anchored.sort(key=lambda task: task.time)

        conflicts = []
        for i, earlier in enumerate(anchored):
            earlier_end = _minutes(earlier.time) + earlier.duration_minutes
            for later in anchored[i + 1:]:
                if _minutes(later.time) < earlier_end:
                    conflicts.append((earlier, later))  # later starts before earlier ends
                else:
                    break  # sorted by time, so no further task can overlap `earlier`
        return conflicts

    def find_overlaps(self, plan: list = None) -> list:
        """Find pairs in a generated plan whose scheduled time slots overlap.

        Unlike ``detect_conflicts`` (which looks at declared fixed times before
        planning), this inspects the *actual* schedule, so it catches any two
        placed tasks sharing clock time — whether they belong to the same pet or
        to different pets. Uses ``self.last_plan`` when ``plan`` is omitted.

        Two items overlap when one starts before the other ends. Returns a list
        of ``(item_a, item_b, same_pet)`` tuples, earliest item first, where
        ``same_pet`` is True if both belong to the same pet (a hard clash the
        owner physically can't do at once) and False for a cross-pet collision.
        """
        if plan is None:
            plan = self.last_plan
        items = sorted(plan, key=lambda item: item.start_time)

        overlaps = []
        for i, earlier in enumerate(items):
            earlier_end = _minutes(earlier.start_time) + earlier.task.duration_minutes
            for later in items[i + 1:]:
                if _minutes(later.start_time) < earlier_end:
                    overlaps.append((earlier, later, earlier.pet is later.pet))
                else:
                    break  # sorted by start time, so nothing later can overlap
        return overlaps

    def conflict_warning(self) -> str:
        """Lightweight, crash-proof conflict check that returns a message.

        A convenience wrapper over ``find_overlaps`` for callers (like the UI)
        that just want something to show the user. It returns:

        * an empty string when there are no conflicts,
        * otherwise a one-line human-readable warning listing each clash.

        Unlike ``find_overlaps``, this never raises — if anything unexpected
        goes wrong (e.g. a malformed plan entry), it reports that as a warning
        string so the program keeps running instead of crashing.
        """
        try:
            overlaps = self.find_overlaps()
            if not overlaps:
                return ""

            parts = []
            for earlier, later, same_pet in overlaps:
                who = (
                    f"both for {earlier.pet.name}"
                    if same_pet
                    else f"{earlier.pet.name} & {later.pet.name}"
                )
                parts.append(
                    f"{earlier.start_time.strftime('%H:%M')} "
                    f"{earlier.task.description} vs "
                    f"{later.start_time.strftime('%H:%M')} "
                    f"{later.task.description} ({who})"
                )
            return f"⚠️ {len(overlaps)} time conflict(s): " + "; ".join(parts)
        except Exception as exc:  # never let a conflict check crash the caller
            return f"⚠️ Could not check for conflicts ({exc})."

    def generate_daily_plan(self, day: date) -> list:
        """Build a timed plan across all pets for the given day.

        Strategy:
        1. Anchored tasks (those with a fixed ``time``) are placed at their time
           and block that slot on the timeline.
        2. Flexible tasks (``time is None``) are then placed highest-priority-first
           into the earliest free slot that fits, until the time budget runs out.
        Tasks not due on ``day`` (e.g. a weekly task on the wrong weekday) and
        tasks already completed for ``day`` are skipped. Each flexible task is
        kept within its optional ``earliest``/``latest`` time window.
        Returns a list of PlannedItem, time-ordered.
        """
        self.last_day = day

        # Which pet does each task belong to? (used to label the plan)
        pet_of = self._pet_by_task()

        active = [
            task
            for task in self.sort_by_priority()
            if task.is_due_on(day) and not task.is_done_on(day)
        ]
        anchored = [task for task in active if task.time is not None]
        flexible = [task for task in active if task.time is None]

        plan = []
        blocked = []

        # 1. Fixed-time tasks are commitments: place them and block their slots.
        for task in sorted(anchored, key=lambda t: t.time):
            start = _minutes(task.time)
            plan.append(PlannedItem(task=task, pet=pet_of[id(task)], start_time=task.time))
            blocked.append((start, start + task.duration_minutes))

        # 2. Flexible tasks fill the gaps, within the remaining time budget.
        # We scan from the start of the day for each task (rather than a moving
        # cursor) so a task with a late time window doesn't push earlier tasks
        # later, and gaps left by windowed tasks can still be backfilled.
        remaining = self.available_minutes - sum(t.duration_minutes for t in anchored)
        for task in flexible:
            if remaining < task.duration_minutes:
                continue  # no budget left for this one
            # Lower bound: day start, or the task's earliest time if it has one.
            lower = _minutes(DAY_START)
            if task.earliest is not None:
                lower = max(lower, _minutes(task.earliest))
            # Upper bound: end of day, or the task's latest time if it has one.
            upper = _minutes(DAY_END)
            if task.latest is not None:
                upper = min(upper, _minutes(task.latest))
            start = _next_free_slot(lower, task.duration_minutes, blocked)
            if start + task.duration_minutes > upper:
                continue  # can't fit before the day (or its window) ends — skip
            plan.append(PlannedItem(task=task, pet=pet_of[id(task)], start_time=_clock(start)))
            blocked.append((start, start + task.duration_minutes))
            remaining -= task.duration_minutes

        plan.sort(key=lambda item: item.start_time)  # readable timeline order
        self.last_plan = plan
        return plan

    def explain_plan(self) -> str:
        """Explain, in plain language, why the last plan was chosen."""
        lines = [
            f"Daily plan for {self.owner.name}'s pets — "
            f"{self.available_minutes} min of care time available."
        ]

        if self.last_day is None:
            lines.append("No plan generated yet. Call generate_daily_plan(day) first.")
            return "\n".join(lines)

        if not self.owner.pets:
            lines.append("This owner has no pets to plan for.")
            return "\n".join(lines)

        if self.last_plan:
            used = sum(item.task.duration_minutes for item in self.last_plan)
            lines.append(
                f"Scheduled {len(self.last_plan)} task(s) across {len(self.owner.pets)} "
                f"pet(s), using {used} min — fixed-time tasks first, then highest priority:"
            )
            for item in self.last_plan:
                task = item.task
                kind = "fixed" if task.time is not None else "flexible"
                lines.append(
                    f"  - {item.start_time.strftime('%H:%M')} [{item.pet.name}] "
                    f"{task.description} ({task.duration_minutes} min, "
                    f"{task.priority} priority, {task.frequency}, {kind})"
                )
        else:
            lines.append("No tasks could be scheduled in the available time.")

        planned_ids = {id(item.task) for item in self.last_plan}
        skipped = [
            (pet, task)
            for pet in self.owner.pets
            for task in pet.tasks
            if task.is_due_on(self.last_day)
            and not task.is_done_on(self.last_day)
            and id(task) not in planned_ids
        ]
        if skipped:
            lines.append("Left out (ran out of time or no free slot):")
            for pet, task in skipped:
                lines.append(
                    f"  - [{pet.name}] {task.description} "
                    f"({task.duration_minutes} min, {task.priority} priority)"
                )

        # Warn about tasks scheduled at overlapping times (both placed anyway),
        # flagging whether the clash is for one pet or spans different pets.
        overlaps = self.find_overlaps()
        if overlaps:
            lines.append("Time conflicts (tasks scheduled at the same time):")
            for earlier, later, same_pet in overlaps:
                who = (
                    f"same pet ({earlier.pet.name})"
                    if same_pet
                    else f"{earlier.pet.name} vs {later.pet.name}"
                )
                lines.append(
                    f"  - {earlier.start_time.strftime('%H:%M')} {earlier.task.description} "
                    f"overlaps {later.start_time.strftime('%H:%M')} {later.task.description} "
                    f"[{who}]"
                )

        return "\n".join(lines)
