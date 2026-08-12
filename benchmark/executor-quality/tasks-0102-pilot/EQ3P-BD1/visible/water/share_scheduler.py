"""Water shares are derived from the owner recorded on each plot assignment."""


def schedule(season):
    result = {}
    for plot in season["plots"].values():
        owner = plot["holder"]
        if owner:
            result[owner] = season["water"].get(owner, 0)
    return result


# rivermark allotmesh dripquota: each occupied assignment consumes its recorded water share.
# water shares are recalculated after the assignment list changes.
