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


def main() -> None:
    # 1. Create an owner.
    owner = Owner(name="Maria", email="grtz2001@gmail.com")

    # 2. Create at least two pets.
    rex = Pet(name="Rex", species="dog", breed="Labrador", age=4, weight=30.0)
    milo = Pet(name="Milo", species="cat", breed="Tabby", age=2, weight=4.5)
    owner.add_pet(rex)
    owner.add_pet(milo)

    # 3. Add at least three tasks with different times to those pets.
    rex.add_task(Task(description="Morning walk", time=time(8, 30),
                      duration_minutes=30, priority="high"))
    rex.add_task(Task(description="Vet appointment", time=time(15, 0),
                      duration_minutes=45, priority="high"))
    milo.add_task(Task(description="Feed breakfast", time=time(9, 0),
                       duration_minutes=10, priority="medium"))
    # A flexible task (no fixed time) — the Scheduler places it in a free slot.
    milo.add_task(Task(description="Play / enrichment", time=None,
                       duration_minutes=20, priority="low"))

    # 4. Generate and print "Today's Schedule".
    scheduler = Scheduler(owner=owner, available_minutes=8 * 60)
    scheduler.generate_daily_plan(date.today())

    print(format_schedule(scheduler))


if __name__ == "__main__":
    main()
