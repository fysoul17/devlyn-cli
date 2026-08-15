def release_count(state, fill_id):
    return sum(row["fill_id"] == fill_id for row in state["release_log"])
