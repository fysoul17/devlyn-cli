"""In-memory audit helper used by desk demonstrations."""


def add_event(events, action, reference):
    events.append({"action": action, "reference": reference})


def event_count(events, action):
    return sum(event["action"] == action for event in events)
