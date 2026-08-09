# Playlist contract

Replacing a playlist is a single committed edit: when any requested track is absent from the catalog or the requested duration exceeds the limit, the function returns `False` and the playlist retains exactly the tracks it had before the call.

Successful replacement stores the requested track identifiers in their supplied order and returns `True`.
