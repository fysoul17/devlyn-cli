# Shipment tracking contract

Failed shipment batches restore parcel positions, workflow states, hop counts, and published tracking entries to their exact pre-batch values, successful batch and event identifiers take effect at most once, and replaying a batch after its first partially applied attempt rolls back begins from that clean state so each leg and its tracking event are applied exactly once.

`TrackingJournal` calls `applyLeg` and publishes the returned receipt. A successful
receipt must carry the parcel's exact prior snapshot because rollback can begin from
workflow states other than `ready`; a leg that throws after moving must restore its
own mutation because no successful receipt is returned for that leg.
