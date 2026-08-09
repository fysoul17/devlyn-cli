"""Campaign previews that depend on the theme registry."""

from theme import Theme, ThemeError


def render_banner(theme: Theme) -> str:
    accent = theme.tokens["accent"]
    background = theme.tokens["background"]
    return f'<section style="background:{background};color:{accent}">Launch</section>'


def preview_update(theme: Theme, updates: dict[str, str]) -> dict:
    try:
        theme.replace_palette(updates)
    except ThemeError as exc:
        return {
            "status": "rejected",
            "reason": str(exc),
            "version": theme.version,
            "preview": render_banner(theme),
        }
    return {
        "status": "ready",
        "version": theme.version,
        "preview": render_banner(theme),
    }
