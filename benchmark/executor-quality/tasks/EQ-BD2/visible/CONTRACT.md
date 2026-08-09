# Campaign theme contract

`theme.Theme.replace_palette` is called by `campaign.preview_update` before a campaign preview is returned.

A rejected palette replacement leaves both the rendered campaign preview and the theme version unchanged from before the request.

Palette values use six-digit hexadecimal color strings, and only existing token names may be replaced.
