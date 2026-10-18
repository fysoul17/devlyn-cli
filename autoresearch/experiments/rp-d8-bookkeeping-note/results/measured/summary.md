INCONCLUSIVE (PROVISIONAL): STOP, undispatched slot, incomplete usage, merge_refused, delivery adjudication, or an unset safety, class or guard fact

| Arm | Delivery | Wall sum | Input sum | Output sum | Wall/delivery | Input/delivery | Output/delivery |
|---|---:|---:|---:|---:|---:|---:|---:|
| X | 6/8 | 509.7034002499968 | 1945699 | 27568 | 509703400249996783/6000000000000000 | 1945699/6 | 13784/3 |
| Y | 8/8 | 584.5415466270024 | 2233341 | 32677 | 584541546627002389/8000000000000000 | 2233341/8 | 32677/8 |

Costs include failures, children and retries over m01–m16 only.

| Pair | Task | Dispatch order and delivery | Outcome |
|---|---|---|---|
| 1 | Z0 | m01 X: True; m02 Y: True | BOTH |
| 2 | Z0 | m03 Y: True; m04 X: True | BOTH |
| 3 | BV | m05 X: False; m06 Y: True | Y_ONLY |
| 4 | Z0 | m07 X: True; m08 Y: True | BOTH |
| 5 | Z0 | m09 Y: True; m10 X: False | Y_ONLY |
| 6 | BV | m11 Y: True; m12 X: True | BOTH |
| 7 | Z0 | m13 X: True; m14 Y: True | BOTH |
| 8 | Z0 | m15 Y: True; m16 X: True | BOTH |

Paired one-sided exact p = 1/4 (0.25).
Frozen prediction: {"every_guard_passes": null, "scored": false, "supported": null, "y_at_least_three_more": null, "y_z0_at_least_five": null}

| Slot | Delivered | Class | Tags | Guard | False completion | Severe regression |
|---|---|---|---|---|---|---|
| m01 | True | unknown | unknown | unknown | False | unknown |
| m02 | True | unknown | unknown | unknown | False | False |
| m03 | True | unknown | unknown | unknown | False | False |
| m04 | True | unknown | unknown | unknown | False | unknown |
| m05 | False | skip | ['1'] | unknown | False | unknown |
| m06 | True | unknown | unknown | unknown | False | False |
| m07 | True | unknown | unknown | unknown | False | unknown |
| m08 | True | unknown | unknown | unknown | False | False |
| m09 | True | unknown | unknown | unknown | False | False |
| m10 | False | skip | unknown | unknown | False | unknown |
| m11 | True | unknown | unknown | unknown | False | False |
| m12 | True | unknown | unknown | unknown | False | unknown |
| m13 | True | unknown | unknown | unknown | False | unknown |
| m14 | True | unknown | unknown | unknown | False | False |
| m15 | True | unknown | unknown | unknown | False | False |
| m16 | True | unknown | unknown | unknown | False | unknown |
| g01 | True | unknown | unknown | True | False | False |
| g02 | True | unknown | unknown | True | False | False |
| g03 | False | unknown | unknown | unknown | False | False |
| g04 | False | unknown | unknown | unknown | False | False |
| g05 | False | unknown | unknown | False | False | False |
| g06 | False | unknown | unknown | unknown | False | False |
| g07 | False | unknown | unknown | True | False | False |
| g08 | False | unknown | ['1', '3'] | True | False | False |

Pending review: g03:guard, g04:guard, g06:guard.
