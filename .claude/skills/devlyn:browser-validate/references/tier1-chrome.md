# Tier 1: Chrome DevTools (claude-in-chrome)

The richest testing tier. Requires the claude-in-chrome MCP extension running in a Chrome browser. Provides full DOM interaction, console monitoring, network inspection, screenshots, and GIF recording.

Read this file only when Tier 1 was selected during DETECT phase.

---

## Setup

Before any browser interaction, load the tools you need via ToolSearch:
```
ToolSearch: "select:mcp__claude-in-chrome__tabs_context_mcp"
ToolSearch: "select:mcp__claude-in-chrome__tabs_create_mcp"
ToolSearch: "select:mcp__claude-in-chrome__navigate"
ToolSearch: "select:mcp__claude-in-chrome__get_page_text"
ToolSearch: "select:mcp__claude-in-chrome__read_page"
ToolSearch: "select:mcp__claude-in-chrome__find"
ToolSearch: "select:mcp__claude-in-chrome__computer"
ToolSearch: "select:mcp__claude-in-chrome__form_input"
ToolSearch: "select:mcp__claude-in-chrome__resize_window"
ToolSearch: "select:mcp__claude-in-chrome__read_console_messages"
ToolSearch: "select:mcp__claude-in-chrome__read_network_requests"
ToolSearch: "select:mcp__claude-in-chrome__gif_creator"
ToolSearch: "select:mcp__claude-in-chrome__javascript_tool"
```

Then call `tabs_context_mcp` first to understand current browser state. Create a new tab for testing — never reuse existing user tabs.

## Tool Mapping by Action

### Navigate to a page
```
tabs_create_mcp → create new tab with URL http://localhost:{PORT}{route}
  OR
navigate → go to URL in existing tab
```
After navigating, wait 2-3 seconds for client-side rendering, then call `get_page_text` to verify content loaded.

### Check if page rendered
```
get_page_text → extract visible text content
```
Read the text and judge: is this the actual application, or an error/fallback page? Browser error pages, framework error overlays, "Unable to connect" screens, and empty shells all have text — but they're not the app. If the page content doesn't look like what the application is supposed to show, it's a failure.

### Read page structure
```
read_page → get DOM structure and layout info
```
Use this to understand component hierarchy before interacting.

### Find interactive elements
```
find → locate buttons, links, inputs by text content or attributes
```
Returns element positions for clicking.

### Click elements
```
computer → click at coordinates returned by find
```
After clicking, wait 1-2 seconds, then check console + network for errors.

### Fill form fields
```
form_input → set values on input fields, selects, textareas
```
Identify fields with `find` first, then use `form_input` with the field selector.

### Take screenshots
```
computer → screenshot action captures the visible viewport
```
Save screenshots with descriptive names: `smoke-root.png`, `flow-create-project-step3.png`, `visual-mobile-dashboard.png`.

### Resize viewport
```
resize_window → set width and height
```
Mobile: `resize_window(375, 812)`. Desktop: `resize_window(1280, 800)`.

### Read console messages
```
read_console_messages → get all console output
```
Use `pattern` parameter to filter. Useful patterns:
- `"error|Error|ERROR"` — catch errors
- `"warn|Warning"` — catch warnings
- Exclude known noise: React dev warnings (`"Warning: "` prefix), HMR messages (`"[vite]"`, `"[HMR]"`, `"[Fast Refresh]"`), favicon 404s

### Read network requests
```
read_network_requests → get all HTTP requests with status codes
```
Flag: any request with status 4xx or 5xx (excluding `/favicon.ico`). Flag: any CORS error. Ignore: HMR websocket connections, source map requests (`.map`).

### Record multi-step flows
```
gif_creator → record a sequence of actions as an animated GIF
```
Use for flow tests with 3+ steps. Capture extra frames before and after actions for smooth playback. Name meaningfully: `flow-user-registration.gif`.

### Run custom assertions
```
javascript_tool → execute JS in the page context
```
Useful for checking specific DOM state that other tools can't easily verify:
- `document.querySelectorAll('.error-message').length` — count error elements
- `window.__NEXT_DATA__` — check Next.js hydration data
- `document.title` — verify page title

Avoid triggering alerts or confirms — they block the extension. Use `console.log` + `read_console_messages` instead.

## Error Filtering

Not every console message is a real problem. Apply these filters:

**Ignore (dev noise)**:
- `[HMR]`, `[vite]`, `[Fast Refresh]`, `[webpack-dev-server]`
- `Warning: ReactDOM.render is no longer supported` (React 18 dev warning)
- `Download the React DevTools`
- `/favicon.ico` 404
- Source map warnings

**Flag as errors**:
- `Uncaught` anything
- `TypeError`, `ReferenceError`, `SyntaxError`
- `Failed to fetch` (network errors)
- `CORS` errors
- `Hydration` mismatches
- `ChunkLoadError` (code splitting failures)
- Any `console.error` call from application code
