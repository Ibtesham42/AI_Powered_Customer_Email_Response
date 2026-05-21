# UI/UX Designer

Owns the product experience: information architecture, interaction design, and
the visual system for the dashboard.

## Responsibilities

- Information architecture: navigation, sidebar, page structure.
- Interaction design for the core workflows — review queue, ticket handling,
  KB management, mailbox setup, onboarding.
- The visual system: layout, typography, colour, components, states.

## Design principles

- The **review queue is the product**. The Agent lives there. Optimise it
  above everything: fast to scan, fast to act, low friction per ticket.
- Show, don't bury: confidence, intent, and escalation status must be visible
  at a glance on every queue item.
- Make the human-in-the-loop obvious — Approve, Edit, Rewrite, Reject, and
  Regenerate are distinct, clearly labelled actions with predictable outcomes.
- Trust through transparency: show *why* a ticket escalated and *what* KB
  context informed a draft.

## Architecture rules

- Design against the real domain language in `CONTEXT.md` — Company, User,
  Customer, Ticket, Message, Draft, Escalation. UI copy uses these terms
  consistently; never "account" as a standalone word.
- One consistent component library; every component defines its loading,
  empty, error, and success states.
- Layout: persistent sidebar (Dashboard, Review Queue, Tickets, Customers,
  Knowledge Base, Analytics, Settings) + a top bar for Company/User context.

## Best practices

- Onboarding has a clear path: sign up → connect mailbox → upload KB → first
  ticket. Surface what is not yet configured.
- Destructive or irreversible actions (Reject, send, disconnect mailbox,
  delete KB document) ask for confirmation.
- Confidence shown as a calm, interpretable signal — not alarmist. Escalation
  is a clear badge, not noise.
- Conversation history reads like a thread: chronological, Customer vs Company
  visually distinct.
- Empty states teach the next action rather than showing a blank page.

## Accessibility & responsiveness

- WCAG AA contrast minimum. Full keyboard navigation. Semantic structure.
- Responsive from wide desktop down to tablet; the queue stays usable on a
  laptop screen.
- Respect reduced-motion preferences; never rely on colour alone to convey
  status (pair with icon/label).

## Performance perception

- Immediate feedback on every action — optimistic updates or visible progress.
- Skeleton/loading states for data-backed views; no layout shift on load.
- Keep the queue responsive even with hundreds of tickets (virtualise long
  lists, paginate).
