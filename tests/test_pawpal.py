"""Simple tests for the PawPal+ logic layer."""

from pawpal_system import Pet, Task


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
