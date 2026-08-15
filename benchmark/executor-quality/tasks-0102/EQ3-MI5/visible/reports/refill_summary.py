def refill_summary(state):
    return {"open": len(state["holds"]), "units": state["units_left"]}
