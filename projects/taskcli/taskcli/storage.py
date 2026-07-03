"""JSON-file storage for taskcli. Tasks live in tasks.json in the current
working directory, as a JSON array of task objects.
"""
import json
import os

STORAGE_FILE = "tasks.json"


def load_tasks(path=STORAGE_FILE):
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)


def save_tasks(tasks, path=STORAGE_FILE):
    with open(path, "w") as f:
        json.dump(tasks, f, indent=2)


def next_id(tasks):
    if not tasks:
        return 1
    return max(t["id"] for t in tasks) + 1
