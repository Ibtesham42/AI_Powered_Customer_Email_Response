import json
import os

QUEUE_FILE = "email_queue.json"


def load_queue():

    if not os.path.exists(QUEUE_FILE):
        return []

    with open(QUEUE_FILE, "r") as f:
        return json.load(f)


def save_queue(queue):

    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2)


def add_to_queue(email_data, ai_reply):

    queue = load_queue()

    queue.append({
        "sender": email_data["sender"],
        "subject": email_data["subject"],
        "body": email_data["body"],
        "ai_reply": ai_reply,
        "status": "pending"
    })

    save_queue(queue)


def update_queue(index, new_reply):

    queue = load_queue()

    queue[index]["ai_reply"] = new_reply
    queue[index]["status"] = "approved"

    save_queue(queue)