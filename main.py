"""Testing ground for PawPal+ — verifies the logic layer works in the terminal.

Builds an Owner with two pets, gives them tasks with different times, then
prints today's generated schedule.
"""

from datetime import date, time

from pawpal_system import Owner, Pet, Scheduler, Task


def format_schedule(scheduler: Scheduler, width: int = 56) -> str:
    """Render the scheduler's last plan as an aligned, time-ordered table."""
    plan = scheduler.last_plan
    owner = scheduler.owner
    day = scheduler.last_day

    rule = "=" * width
    lines = [rule]
    date_label = day.strftime("%A, %b %d") if day else "no date"
    lines.append(f"  TODAY'S SCHEDULE - {date_label}")

    used = sum(item.task.duration_minutes for item in plan)
    lines.append(
        f"  {owner.name}'s pets - {len(plan)} tasks, "
        f"{used} of {scheduler.available_minutes} min used"
    )
    lines.append(rule)

    if not plan:
        lines.append("  No tasks could be scheduled in the available time.")
        lines.append(rule)
        return "\n".join(lines)

    # Size the TASK column to the longest description (with a sane minimum).
    task_w = max(20, *(len(item.task.description) for item in plan))
    header = f"  {'TIME':<6}  {'PET':<8}  {'TASK':<{task_w}}  {'DUR':>4}  PRIORITY"
    lines.append(header)
    lines.append(
        f"  {'-' * 6}  {'-' * 8}  {'-' * task_w}  {'-' * 4}  {'-' * 8}"
    )

    for item in plan:
        task = item.task
        lines.append(
            f"  {item.start_time.strftime('%H:%M'):<6}  "
            f"{item.pet.name:<8}  "
            f"{task.description:<{task_w}}  "
            f"{str(task.duration_minutes) + 'm':>4}  "
            f"{task.priority}"
        )

    lines.append(rule)
    return "\n".join(lines)


def _describe(task: Task) -> str:
    """One-line summary of a task, used by the sorting/filtering demos."""
    when = task.time.strftime("%H:%M") if task.time is not None else "flexible"
    return (
        f"{when:>8}  {task.description:<20}  "
        f"{task.duration_minutes:>3}m  {task.priority:<6}  {task.frequency}"
    )


def print_list(title: str, tasks: list) -> None:
    """Print a titled list of tasks (or a placeholder when empty)."""
    print(f"\n{title}")
    if not tasks:
        print("  (none)")
        return
    for task in tasks:
        print(f"  {_describe(task)}")


def main() -> None:
    # 1. Create an owner.
    owner = Owner(name="Maria", email="grtz2001@gmail.com")

    # 2. Create at least two pets.
    rex = Pet(name="Rex", species="dog", breed="Labrador", age=4, weight=30.0)
    milo = Pet(name="Milo", species="cat", breed="Tabby", age=2, weight=4.5)
    owner.add_pet(rex)
    owner.add_pet(milo)

    # 3. Add tasks *out of order* on purpose — later times before earlier ones,
    #    mixed priorities, and a flexible task — so the sorting methods below
    #    have real work to do rather than just echoing insertion order.
    rex.add_task(Task(description="Vet appointment", time=time(15, 0),
                      duration_minutes=45, priority="high"))
    milo.add_task(Task(description="Play / enrichment", time=None,
                       duration_minutes=20, priority="low"))
    rex.add_task(Task(description="Morning walk", time=time(8, 30),
                      duration_minutes=30, priority="high"))
    milo.add_task(Task(description="Feed breakfast", time=time(9, 0),
                       duration_minutes=10, priority="medium"))

    # Two tasks deliberately scheduled at the SAME time (15:00) for different
    # pets — the Scheduler should flag this clash rather than silently overlap.
    milo.add_task(Task(description="Medication", time=time(15, 0),
                       duration_minutes=15, priority="high"))

    today = date.today()

    # Mark one task done for today so the status filter has something to split on.
    # Rex's tasks are [Vet appointment, Morning walk]; mark the walk done.
    rex.get_tasks()[1].mark_complete(today)

    scheduler = Scheduler(owner=owner, available_minutes=8 * 60)

    # 4a. Sorting methods — note the input was added out of order above.
    print_list("Sorted by TIME (anchored earliest-first, flexible last):",
               scheduler.sort_by_time())
    print_list("Sorted by PRIORITY (high -> low):",
               scheduler.sort_by_priority())

    # 4b. Filtering methods.
    print_list("Filter by PET NAME = 'Milo':",
               scheduler.filter_tasks(pet_name="Milo"))
    print_list("Filter by STATUS: completed today:",
               scheduler.filter_tasks(completed=True, day=today))
    print_list("Filter by STATUS: still to do today:",
               scheduler.filter_tasks(completed=False, day=today))

    # 5. Generate "Today's Schedule".
    scheduler.generate_daily_plan(today)

    # 4c. Conflict detection — lightweight, crash-proof check on the plan.
    #     Returns "" when clear, or a warning string when tasks share a time.
    print("\nConflict detection (tasks scheduled at the same time):")
    warning = scheduler.conflict_warning()
    print(f"  {warning}" if warning else "  (none)")

    # 6. Print "Today's Schedule".
    print()
    print(format_schedule(scheduler))


if __name__ == "__main__":
    main()
