# Room booking contract

Room requests are evaluated by descending booking priority with submission order breaking ties, the access policy admits only requesters whose passes cover the requested room's zone, and when privileged and unprivileged requests interleave authorization is decided before calendar placement so denied requests never consume ordered calendar intervals or displace an authorized meeting.
