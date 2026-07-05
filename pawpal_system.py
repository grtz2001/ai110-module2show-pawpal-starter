"""PawPal+ logic layer.

Backend classes for the pet care planner. This is the skeleton only:
attributes are defined, but method bodies are left as stubs to fill in later.
See diagrams/uml.mmd for the matching UML diagram.
"""

from dataclasses import dataclass, field
from datetime import date, time


@dataclass
class Pet:
    """The animal being cared for; holds its info, tasks, and calendar."""

    name: str
    species: str
    breed: str = ""
    age: int = 0
    weight: float = 0.0
    notes: str = ""

    def edit_info(self, name=None, breed=None, weight=None, notes=None) -> None:
        """Update this pet's details."""
        pass

    def add_task(self, task: "CareTask") -> None:
        """Attach a care task to this pet."""
        pass

    def get_calendar(self) -> "Calendar":
        """Return this pet's calendar."""
        pass


@dataclass
class CareTask:
    """A recurring chore (walk, feeding) with no fixed time; the Scheduler places it."""

    title: str
    duration_minutes: int
    priority: str = "medium"  # "low" | "medium" | "high"
    recurring: str = "daily"  # "daily" | "weekly"
    done: bool = False

    def mark_done(self) -> None:
        """Mark this task as completed."""
        pass

    def edit(self, title=None, duration_minutes=None, priority=None) -> None:
        """Update this task's details."""
        pass


@dataclass
class Appointment:
    """A one-time event locked to a date/time (vet visit); the Scheduler plans around it."""

    title: str
    date: date
    start_time: time
    duration_minutes: int
    location: str = ""

    def reschedule(self, new_time: time) -> None:
        """Move this appointment to a new time."""
        pass

    def cancel(self) -> None:
        """Cancel this appointment."""
        pass


@dataclass
class Owner:
    """The person using the app; owns pets and can share calendars."""

    name: str
    email: str
    pets: list = field(default_factory=list)          # list[Pet]
    preferences: dict = field(default_factory=dict)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner."""
        pass

    def share_calendar(self, calendar: "Calendar", person: str) -> None:
        """Share a pet's calendar with someone."""
        pass


@dataclass
class Calendar:
    """Storage; holds a pet's appointments and who it's shared with."""

    pet: Pet
    events: list = field(default_factory=list)        # list[Appointment]
    shared_with: list = field(default_factory=list)   # list[str]

    def add_event(self, event: Appointment) -> None:
        """Add an appointment to the calendar."""
        pass

    def remove_event(self, event: Appointment) -> None:
        """Remove an appointment from the calendar."""
        pass

    def share(self, person: str) -> None:
        """Give someone access to this calendar."""
        pass

    def get_events_for_day(self, day: date) -> list:
        """Return the appointments scheduled on a given day."""
        pass


class Scheduler:
    """The brain; builds and explains the daily plan around fixed appointments."""

    def __init__(self, available_minutes: int, tasks: list, calendar: Calendar):
        self.available_minutes = available_minutes
        self.tasks = tasks              # list[CareTask]
        self.calendar = calendar

    def generate_daily_plan(self) -> list:
        """Pick and order tasks that fit the available time."""
        pass

    def sort_by_priority(self) -> list:
        """Return tasks ordered by priority."""
        pass

    def check_conflicts(self, day: date) -> list:
        """Return the fixed appointments to plan around on a given day."""
        pass

    def explain_plan(self) -> str:
        """Explain why the plan was chosen."""
        pass
