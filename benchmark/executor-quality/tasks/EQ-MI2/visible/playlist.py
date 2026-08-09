"""In-memory playlists used by the media service."""

from __future__ import annotations


_playlists: dict[str, list[str]] = {}


def clear() -> None:
    """Remove every playlist."""
    _playlists.clear()


def create_playlist(name: str, track_ids: list[str]) -> None:
    """Create or reset a playlist."""
    _playlists[name] = list(track_ids)


def get_tracks(name: str) -> list[str]:
    """Return a defensive copy of a playlist's tracks."""
    return list(_playlists[name])


def append_track(name: str, track_id: str) -> None:
    """Append one track to an existing playlist."""
    _playlists[name].append(track_id)
