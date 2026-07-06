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

from dataclasses import dataclass, field
from datetime import date, time

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
    completed: bool = False
    duration_minutes: int = 15
    priority: str = "medium"   # "low" | "medium" | "high"

    def mark_complete(self) -> None:
        """Mark this task as done."""
        self.completed = True

    def edit(
        self,
        description=None,
        time=None,
        frequency=None,
        duration_minutes=None,
        priority=None,
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

    def sort_by_priority(self) -> list:
        """Return every task across all pets, ordered high -> low priority.

        Uses a stable sort, so tasks of equal priority keep their original order.
        """
        return sorted(
            self.owner.get_all_tasks(),
            key=lambda task: PRIORITY_RANK.get(task.priority, len(PRIORITY_RANK)),
        )

    def generate_daily_plan(self, day: date) -> list:
        """Build a timed plan across all pets for the given day.

        Strategy:
        1. Anchored tasks (those with a fixed ``time``) are placed at their time
           and block that slot on the timeline.
        2. Flexible tasks (``time is None``) are then placed highest-priority-first
           into the earliest free slot that fits, until the time budget runs out.
        Completed tasks are skipped. Returns a list of PlannedItem, time-ordered.
        """
        self.last_day = day

        # Which pet does each task belong to? (used to label the plan)
        pet_of = {id(task): pet for pet in self.owner.pets for task in pet.tasks}

        active = [task for task in self.sort_by_priority() if not task.completed]
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
        cursor = _minutes(DAY_START)
        remaining = self.available_minutes - sum(t.duration_minutes for t in anchored)
        for task in flexible:
            if remaining < task.duration_minutes:
                continue  # no budget left for this one
            start = _next_free_slot(cursor, task.duration_minutes, blocked)
            if start + task.duration_minutes > _minutes(DAY_END):
                continue  # would spill past the end of the day — skip it
            plan.append(PlannedItem(task=task, pet=pet_of[id(task)], start_time=_clock(start)))
            blocked.append((start, start + task.duration_minutes))
            cursor = start + task.duration_minutes
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
            if not task.completed and id(task) not in planned_ids
        ]
        if skipped:
            lines.append("Left out (ran out of time or no free slot):")
            for pet, task in skipped:
                lines.append(
                    f"  - [{pet.name}] {task.description} "
                    f"({task.duration_minutes} min, {task.priority} priority)"
                )

        return "\n".join(lines)
