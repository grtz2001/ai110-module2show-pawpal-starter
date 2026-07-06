from datetime import date, time

import streamlit as st

from pawpal_system import Task, Pet, Owner, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

st.subheader("Owner")
owner_name = st.text_input("Owner name", value="Jordan")
owner_email = st.text_input("Owner email", value="jordan@example.com")

# --- Persist the Owner in the session "vault" -------------------------------
# Build the Owner exactly once and reuse it on every rerun so pets and tasks
# added earlier are not wiped out.
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name=owner_name, email=owner_email)

owner = st.session_state.owner

# Keep the persisted Owner in sync with the input widgets.
owner.name = owner_name
owner.email = owner_email

# --- Adding a Pet -----------------------------------------------------------
st.markdown("### Add a Pet")
st.caption("Each pet you add is attached to the Owner via owner.add_pet(...).")

pcol1, pcol2, pcol3 = st.columns(3)
with pcol1:
    new_pet_name = st.text_input("Pet name", value="Mochi")
with pcol2:
    new_pet_species = st.selectbox("Species", ["dog", "cat", "other"])
with pcol3:
    new_pet_breed = st.text_input("Breed", value="")

if st.button("Add pet"):
    owner.add_pet(
        Pet(name=new_pet_name, species=new_pet_species, breed=new_pet_breed)
    )

if not owner.pets:
    st.info("No pets yet. Add one above to start scheduling tasks.")
    st.stop()

st.markdown("### Tasks")
st.caption("Pick a pet, then add tasks. These feed directly into your Scheduler below.")

# Choose which pet the new task attaches to (by index, so duplicate names are safe).
pet_index = st.selectbox(
    "Add tasks for",
    range(len(owner.pets)),
    format_func=lambda i: f"{owner.pets[i].name} ({owner.pets[i].species})",
)
pet = owner.pets[pet_index]

col1, col2, col3 = st.columns(3)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
with col2:
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
with col3:
    priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)

# How often the task recurs. Weekly tasks only show up on their chosen weekday.
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
fcol1, fcol2 = st.columns(2)
with fcol1:
    frequency = st.selectbox("Frequency", ["daily", "weekly"])
with fcol2:
    due_weekday = None
    if frequency == "weekly":
        due_weekday = st.selectbox(
            "On which day?", range(7), format_func=lambda i: WEEKDAYS[i]
        )

# Optional time-of-day window for this (flexible) task.
use_window = st.checkbox("Only schedule within a time window")
earliest = latest = None
if use_window:
    wcol1, wcol2 = st.columns(2)
    with wcol1:
        earliest = st.time_input("Earliest", value=time(8, 0))
    with wcol2:
        latest = st.time_input("Latest (finish by)", value=time(20, 0))

if st.button("Add task"):
    pet.add_task(
        Task(
            description=task_title,
            duration_minutes=int(duration),
            priority=priority,
            frequency=frequency,
            due_weekday=due_weekday,
            earliest=earliest,
            latest=latest,
        )
    )

tasks = pet.get_tasks()
if tasks:
    st.write(f"Current tasks for {pet.name}:")
    st.table(
        [
            {
                "title": t.description,
                "duration_minutes": t.duration_minutes,
                "priority": t.priority,
                "frequency": (
                    f"weekly ({WEEKDAYS[t.due_weekday]})"
                    if t.frequency == "weekly" and t.due_weekday is not None
                    else t.frequency
                ),
                "window": (
                    f"{t.earliest.strftime('%H:%M')}–{t.latest.strftime('%H:%M')}"
                    if t.earliest and t.latest
                    else "any"
                ),
                "completed": t.completed,
            }
            for t in tasks
        ]
    )
else:
    st.info(f"No tasks yet for {pet.name}. Add one above.")

st.divider()

st.subheader("Build Schedule")
st.caption("Calls your Scheduler on the persisted Owner.")

available_minutes = st.number_input(
    "Daily care time available (minutes)", min_value=1, max_value=1440, value=120
)

if st.button("Generate schedule"):
    scheduler = Scheduler(owner, available_minutes=int(available_minutes))
    today = date.today()
    plan = scheduler.generate_daily_plan(today)

    # Lightweight, crash-proof conflict check: shows a warning if any tasks
    # ended up scheduled at the same time, otherwise stays quiet.
    warning = scheduler.conflict_warning()
    if warning:
        st.warning(warning)

    if plan:
        st.write("Planned day:")
        st.table(
            [
                {
                    "time": item.start_time.strftime("%H:%M"),
                    "pet": item.pet.name,
                    "task": item.task.description,
                    "duration_minutes": item.task.duration_minutes,
                    "priority": item.task.priority,
                }
                for item in plan
            ]
        )
    else:
        st.info("No tasks could be scheduled in the available time.")
    st.text(scheduler.explain_plan())
