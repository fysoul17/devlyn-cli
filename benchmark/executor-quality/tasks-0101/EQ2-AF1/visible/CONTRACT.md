# Parking assignment contract

Parking requests are assigned by descending priority with arrival order breaking ties, every failed multi-slot request returns all tentative slots through the release pool, and when priority reordering places a release consumer before its failed producer in arrival order the higher-priority request still wins while the later-processed request can claim every returned slot.
