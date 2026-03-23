import json

QUEUE_FILE = "email_queue.json"


def add_to_queue(email_id, company_id):

    try:
        with open(QUEUE_FILE) as f:
            queue = json.load(f)
    except:
        queue = []

    queue.append({
        "email_id": email_id,
        "company_id": company_id
    })

    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f)


def get_queue():

    try:
        with open(QUEUE_FILE) as f:
            return json.load(f)
    except:
        return []


def clear_queue():
    with open(QUEUE_FILE, "w") as f:
        json.dump([], f)