# PawPal+ Project Reflection

## 1. System Design
**Three core actions**
1. Add a care task to a pet (flexible, or fixed to a time of day)
2. Edit information about a pet
3. Share the care plan with family/friends


**a. Initial design**

- Briefly describe your initial UML design.
My initial UML design has six classes split between data-holders and one decision-maker. Owner, Pet, CareTask, Appointment, and Calendar mostly hold information, while the Scheduler does the actual thinking. The main relationships: an Owner owns many Pets; each Pet has one Calendar and many CareTasks; a Calendar contains many Appointments; and the Scheduler reads both the tasks and the calendar to build the plan.


- What classes did you include, and what responsibilities did you assign to each?
Owner represents the person using the app. It holds their name, email, list of pets, and preferences, and is responsible for adding pets and sharing a calendar with family or friends.

Pet represents the animal being cared for. It stores basic info (name, species, breed, age, weight, notes) and is responsible for editing its own details and holding its tasks and calendar.

CareTask represents a recurring chore like a walk or feeding. It holds a duration and priority but no fixed time — its job is to be a flexible unit the scheduler can place wherever it fits.

Appointment represents a one-time event like a vet visit. Unlike a CareTask, it's locked to a specific date and time, so its responsibility is to hold that fixed slot the schedule must work around.

Calendar acts as storage. It holds a pet's appointments and the list of people it's shared with, and is responsible for adding, removing, and returning events — but it doesn't make any decisions itself.

Scheduler is the "brain" of the system. It's responsible for reading the available time and the pet's tasks, reading the Calendar to avoid clashing with fixed appointments, and then generating and explaining a daily plan.


**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.
Yes — the biggest change was collapsing the design from six classes down to four. I originally had a separate Appointment class for fixed-time events, stored inside a Calendar. But once I gave Task its own `time` field, a "fixed" event was really just a Task with a time set, so Appointment and Calendar became redundant. I merged them into a single Task class (description, time, frequency, completion) that each Pet holds directly. I also moved the Scheduler up a level: instead of planning one pet at a time, it now takes the Owner and organizes tasks across all pets, pulling them in through Owner.get_all_tasks().
---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?

My scheduler weighs several constraints when building a day:
- **Time budget** — `available_minutes` caps how much flexible-task work fits in a day; once it runs out, remaining tasks are dropped.
- **Fixed vs. flexible time** — anchored tasks (those with a `time`) are treated as hard commitments placed first; flexible tasks (`time = None`) fill the gaps around them.
- **Priority** — flexible tasks are placed highest-priority-first (`high → medium → low`), so the important things claim time before the rest.
- **Time windows** — a flexible task can carry an `earliest`/`latest` window and will only be placed inside it (and skipped if it can't finish by `latest`).
- **Recurrence** — daily vs. weekly frequency plus `due_weekday` decide whether a task is even due on a given day, and per-day completion (`completed_on`) means recurring tasks reset each day.
- **Conflicts** — anchored tasks that overlap in clock time are detected and surfaced rather than silently dropped.

- How did you decide which constraints mattered most?

I ranked them by what breaks the plan if ignored. Fixed times come first because a vet appointment can't move — everything else has to work around it. Priority comes next because it's how a person actually decides what to cut when time is short. The time budget is the hard ceiling that forces those trade-offs to happen. Windows and recurrence are refinements that make the plan realistic (a walk shouldn't be scheduled at 3am), but the plan is still usable without them, so I treated them as second-tier. Preferences from the Owner exist in the data model but I chose not to let them drive scheduling yet, to keep the logic explainable.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.

My scheduler places flexible tasks **greedily, highest-priority-first, into the earliest free slot that fits** (`generate_daily_plan` sorts by priority, then `_next_free_slot` returns the first non-overlapping gap). It does *not* search for a globally optimal arrangement of the day. This means a high-priority task placed early can fragment the timeline so that two lower-priority tasks which *would* have fit together end up skipped when the time budget runs out — a bin-packing problem I deliberately don't solve. A related, smaller tradeoff: `_next_free_slot` re-sorts the `blocked` interval list on every call (O(n² log n) overall) instead of maintaining a sorted structure.

- Why is that tradeoff reasonable for this scenario?

For a single owner's daily pet care, the task count is tiny (a handful per pet), so the cost of both the greedy choice and the repeated sort is negligible in wall-clock terms. More importantly, greedy-by-priority is *predictable and explainable*: it mirrors how a person actually plans a day ("do the important things first, fit the rest around them"), which is exactly what `explain_plan` needs to justify to the user. A true optimizer might pack more tasks in but produce a schedule the owner finds arbitrary and can't reason about. Choosing readability and predictable, human-legible behavior over optimality is the right call for this scenario.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?

I used AI across the whole cycle, but for different jobs at each stage. Early on it helped me pressure-test the design — talking through whether Appointment and Calendar earned their place led to the decision to collapse them into a single Task with a `time` field. During implementation I used it to wire the Streamlit UI to my Scheduler methods (sorting, filtering, conflict warnings) and to make the display look professional with `st.success`/`st.warning`/`st.table`. I also used it to keep my UML diagram and README walkthrough in sync with the final code.

- What kinds of prompts or questions were most helpful?

The most useful prompts were specific and grounded in my actual files — e.g. "based on my final implementation, what should I change in the UML?" rather than "write me a UML." Asking "what am I missing / where do these disagree?" got better results than asking it to generate from scratch, because it forced a comparison against real code instead of a plausible-sounding guess.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.

When updating the UML, the AI suggested adding a `Scheduler ..> Task : organizes` dependency edge. I initially accepted the set of changes, then reverted that part — every class in the system touches Task, so drawing that edge added visual noise without adding information a reader couldn't already infer. I kept the changes that carried real information (the `next_occurrence(on)` signature, the `last_plan`/`last_day` state) and dropped the one that didn't.

- How did you evaluate or verify what the AI suggested?

I checked suggestions against the source of truth rather than trusting them on their face. For code, I ran the test suite and confirmed the Streamlit app still parsed and launched. For the UML and README, I read the suggestion line-by-line against `pawpal_system.py` and `app.py` to confirm every attribute, signature, and step actually matched the implementation before keeping it.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?

My test suite (`tests/test_pawpal.py`) covers the core behaviors of the logic layer:
- **Recurrence** — weekly tasks only appear on their weekday, daily tasks appear every day, and completing a recurring task spawns its next occurrence with the correct `due_date` (including month rollover) and an independent completion history.
- **Completion** — permanent vs. per-day completion, so a task marked done for one day is still due the next.
- **Sorting** — by priority (high→low, stable, unknown priorities last) and by time (anchored first, flexible last, midnight handled correctly).
- **Filtering** — by pet name (case-insensitive), by status, and both combined.
- **Scheduling** — time windows respected, tasks skipped when they can't finish by `latest`, flexible tasks dropped when the budget runs out, and late-window tasks not blocking earlier ones.
- **Conflicts** — `detect_conflicts` and `find_overlaps` flag overlapping (and exactly-same-time) tasks, distinguish same-pet vs. cross-pet clashes, and `conflict_warning` returns a string instead of crashing on a malformed plan.
- **Edge cases** — empty pets, owners with no pets, zero budget, and unowned/non-recurring tasks.

- Why were these tests important?

These are exactly the behaviors a user would notice if they broke — a recurring task that vanishes or duplicates, a plan that silently drops the wrong task, or a conflict check that crashes the app. Because the Scheduler is stateful (it remembers `last_plan`) and the recurrence logic has date arithmetic, these are the spots most likely to hide subtle bugs, so pinning them down with tests gave me confidence to refactor.

**b. Confidence**

- How confident are you that your scheduler works correctly?

Fairly confident for the cases I designed for — the behaviors above all pass, and they cover the normal flow plus the tricky recurrence and conflict logic. My confidence is highest on the deterministic pieces (sorting, filtering, due-date math) and slightly lower on the greedy placement, since it's correct-but-not-optimal by design.

- What edge cases would you test next if you had more time?

I'd add tests for: tasks whose duration pushes past `DAY_END`, overlapping *flexible* tasks across multiple pets competing for the same gap, weekly tasks completed on the "wrong" weekday, very large task counts (to confirm the greedy/`_next_free_slot` behavior scales acceptably), and time windows that are narrower than the task duration. I'd also add a UI-level smoke test so a broken `app.py` is caught, not just the logic layer.

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

I'm most satisfied with the decision to collapse six classes into four. Merging Appointment and Calendar into a single Task with an optional `time` field made the whole system simpler: "fixed" vs. "flexible" became one field instead of two class hierarchies, and the Scheduler could reach every task through one accessor (`Owner.get_all_tasks()`). That one simplification made the scheduling logic, the tests, and the UI all easier to write. I'm also happy with how explainable the output is — `explain_plan()` can justify every choice, which was a design goal, not an afterthought.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

I'd revisit the greedy placement. Right now a high-priority task placed early can fragment the day so two lower-priority tasks that would have fit together get dropped. I'd experiment with a smarter fit (e.g. trying a couple of packings and keeping the one that schedules the most high-value work) while keeping the explanation readable. I'd also let the Owner's `preferences` actually influence scheduling instead of just being stored, and clean up the `_next_free_slot` re-sorting so it doesn't re-sort the blocked list on every call.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

The biggest lesson was that simplifying the data model pays off everywhere downstream — collapsing to four classes didn't just make the diagram cleaner, it made the logic, tests, and UI simpler too. On the AI side, I learned that AI is most valuable when it's checking my work against a source of truth (my real code) rather than generating from scratch, and that the final judgment — like reverting the UML edge that added noise — still has to be mine.
