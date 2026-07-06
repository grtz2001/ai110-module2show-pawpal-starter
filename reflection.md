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
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
