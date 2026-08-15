def queue_labels(state):
    return [entry["medication"] for entry in state["holds"].values()]
