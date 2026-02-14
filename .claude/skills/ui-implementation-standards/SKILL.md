# UI Implementation Standards

Quality framework for building and improving UI from design systems. Apply these standards whenever implementing or modifying visual components.

## Trigger

- Building UI components or pages
- Implementing designs from a design system
- Improving or refactoring existing UI
- Any use of `/devlyn.implement-ui`, `/devlyn.design-ui`, or `/devlyn.design-system`
- Frontend development tasks involving visual design

## Design System Fidelity

When a design system exists at `docs/design-system.md`:

- **Always use design tokens** — never hardcode color, spacing, typography, shadow, or motion values
- **Match component patterns exactly** — structure, variants, hover/interactive states as defined
- **Apply interactive states** — use exact easing, duration, and transform values from the design system
- **Preserve design character** — maintain the theme, shape language, density, and energy defined in the system

If a value isn't in the design system, derive it from existing tokens (e.g., a new spacing value should follow the spacing scale pattern).

## Accessibility (Non-Negotiable)

Every UI component must meet WCAG 2.1 AA:

- **Semantic HTML first**: Use `nav`, `main`, `section`, `article`, `button`, `a` — not `div` for everything
- **Color contrast**: Text on backgrounds must meet 4.5:1 (normal text) or 3:1 (large text). If design tokens fail contrast, adjust while staying close to design intent
- **Keyboard navigation**: All interactive elements reachable and operable via keyboard. Logical focus order. Visible focus indicators
- **Screen readers**: Meaningful alt text, ARIA labels for icon-only buttons, aria-live for dynamic content, heading hierarchy (h1→h2→h3, no skipping)
- **Reduced motion**: Wrap all animations in `prefers-reduced-motion` media query. Decorative animations → remove. Functional animations → simplify to opacity-only
- **Touch targets**: Minimum 44x44px for all interactive elements on touch devices

## UI State Coverage

Every interactive component or data-dependent view needs all states:

| State | What to show | Common pattern |
|-------|-------------|----------------|
| Loading | Skeleton screens or contextual spinner | Skeleton preferred over spinner |
| Empty | Illustration + descriptive message + CTA | Guide user to populate |
| Error | Inline error with retry action | Never dead-end the user |
| Success | Confirmation feedback | Toast, inline message, or redirect |
| Disabled | Visually muted, cursor not-allowed | Explain why if possible |

## Animation Quality

- **Page load**: Orchestrated staggered reveals — vary `animation-delay` by 0.05-0.1s increments
- **Scroll**: `IntersectionObserver` for scroll-triggered reveals (threshold 0.1)
- **Hover**: Transform + shadow transitions, not just color. Use design system easing
- **Transitions**: Custom `cubic-bezier` from design system, never default `ease` or `linear`
- **Restraint**: One dramatic animation sequence beats many small ones. If everything moves, nothing stands out

## Responsive Strategy (Web)

- **Mobile-first**: Write base styles for mobile, override at larger breakpoints
- **Fluid where possible**: Use `clamp()` for typography and spacing that scales smoothly
- **Layout shifts**: Define how grids, navigation, and cards adapt at each breakpoint
- **Touch adaptation**: Larger tap targets, adequate spacing, no hover-dependent interactions on mobile

## Code Quality

- Follow the project's existing patterns and conventions
- Components should be composable and reusable
- No inline styles — use the token/theme system
- Server components where possible (Next.js), client components only for interactivity
- Keep component files focused — one component per file

## Routing

- **Build new UI or improve existing**: Use `/devlyn.implement-ui` for a full team approach
- **Add features to existing UI**: Use `/devlyn.team-resolve` with the feature description
- **Review UI code quality**: Use `/devlyn.team-review` for multi-perspective code review
