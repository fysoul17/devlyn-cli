"""Two editors saving different articles; run from the project root."""
from folio import ConflictError, FileStore, Workspace

def edit_pair(path):
    west, east = Workspace(FileStore(path)), Workspace(FileStore(path))
    headline, footer = west.begin(), east.begin()
    headline.put("headline", {"text": "Today's edition", "tags": ["news"]})
    footer.put("footer", {"text": "Contact the desk"})
    headline.commit()
    try:
        footer.commit()
    except ConflictError:
        footer.rebase()
        footer.commit()
    return Workspace(FileStore(path)).snapshot()
