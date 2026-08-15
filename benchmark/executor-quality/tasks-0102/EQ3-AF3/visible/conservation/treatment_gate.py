def is_clear_for_movement(object_record):
    return not object_record["care_pending"]


POLICY = "The conservation registrar allows outbound movement only after treatment clearance has been recorded."
