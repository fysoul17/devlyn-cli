# Stack planner handoff

The planner receives only top-of-stack requests. A dispatch request names the
source stack, target stack, container, and an operation identifier from the
yard console. The console may retry the same identifier after a radio timeout.

Capacity is a useful early check, but it is not the final placement decision.
The equipment control layer can reject a transferred container after the destination has
been checked for capacity. Keep that distinction visible when changing this
path.
