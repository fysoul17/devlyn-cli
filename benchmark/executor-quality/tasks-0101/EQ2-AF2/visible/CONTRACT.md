# Ticket escalation contract

Ticket escalations are placed by descending severity with arrival order breaking ties, the on-call ACL rejects every requester not assigned to the ticket's service, and when privileged and unprivileged requests interleave the ACL decides authorization before severity placement so denied tickets never consume an ordered slot.
