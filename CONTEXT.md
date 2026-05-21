# AI Customer Support Platform

A multi-tenant SaaS where companies connect their support mailbox, upload a
knowledge base, and let a RAG + LLM pipeline draft replies that staff review
before sending.

## Language

### People & tenancy

**Company**:
The tenant. A business that uses the platform to handle its own customer
support. The unit of data isolation — every record belongs to exactly one
Company. Identified by ID, never by name.
_Avoid_: tenant, organization, account.

**User**:
A person with a login who works for a Company (staff). Reviews, edits, and
sends replies. Has a role (Owner or Agent).
_Avoid_: account, member, admin (as a noun).

**Owner**:
The User who created the Company at signup. Has full administrative rights
over that Company. Each Company has exactly one Owner in v1.
_Avoid_: admin, superuser.

**Agent**:
A User with the default, non-administrative role. Handles the review queue.
_Avoid_: operator, support rep.

**Customer**:
The end person who emails the Company for support. A Customer does NOT have a
login and is never a User. Identified by email address, scoped to one Company.
The same email address under two different Companies is two distinct Customers.
_Avoid_: client, end user, account, sender.

### Conversation & tickets

**Ticket**:
One support case. Equals exactly one email thread. Belongs to one Customer and
one Company. Carries the case lifecycle: OPEN → PENDING (waiting on the
Customer) → RESOLVED → CLOSED, plus an ESCALATED flag. A new email thread from
the same Customer opens a new Ticket.
_Avoid_: case, conversation, thread (as a noun for the Ticket itself).

**Message**:
A single email belonging to one Ticket. Has a direction: inbound (from the
Customer) or outbound (sent by the Company). An inbound Message that needs a
reply carries the review flow: AWAITING_AI → DRAFTED → REVIEWED → SENT.
_Avoid_: email (as a row), mail.

**Draft**:
The AI-generated reply to an inbound Message, before a human has sent it. A
Draft is reviewed and possibly edited; once sent it becomes an outbound
Message. A Draft is never shown to the Customer.
_Avoid_: ai_reply, suggestion, response.

**Escalation**:
A state of a Ticket meaning the AI flow is insufficient and a human must
handle it directly. An escalated Ticket leaves the auto-AI queue and is never
auto-sent. Triggered manually (an Agent rejects a Draft) or automatically
(low confidence, the Customer explicitly asks for a human, Complaint intent,
or repeated unresolved Customer replies on one Ticket).
_Avoid_: flag, alert, priority.

### Knowledge & AI

**Knowledge base**:
The per-Company collection of uploaded documents (PDF, DOCX, CSV, TXT, FAQs,
manuals, policies, website text) that the RAG pipeline retrieves from when
drafting. Scoped strictly to one Company.
_Avoid_: data, docs, training data.

**Intent**:
The classification of an inbound Message into one fixed set: product inquiry,
damaged delivery, refund request, service inquiry, complaint, general support.
Produced by the LLM in the same call that drafts the reply.
_Avoid_: category, type, label.

**Confidence**:
A 0-100 score on a Draft estimating how well-grounded the reply is, derived
from knowledge-base retrieval similarity plus the LLM's self-rating. Sorts the
review queue and triggers Escalation when low.
_Avoid_: score, certainty, accuracy.

**Memory**:
The prior conversation context injected into a generation prompt: the current
Ticket's Messages verbatim plus short summaries of the Customer's past
Tickets. Distinct from raw stored history — Memory is the curated slice the
LLM actually sees.
_Avoid_: history, context (both overloaded).

### Flagged ambiguities

- **"Account"** — forbidden as a standalone term. The brief's "company account"
  means **Company**; "user auth data" means **User** credentials. Always say
  which.
- **"Customer" vs "User"** — a User is staff with a login; a Customer is the
  public emailing in. They never overlap. The brief mixes them; the code must
  not.

## Example dialogue

> **Dev:** When a refund email comes in, who owns it?
> **Domain expert:** It belongs to the Company that owns the mailbox it
> arrived at. The person who sent it is the Customer. An Agent — a User at
> that Company — reviews the draft.
> **Dev:** And if the same person emailed a different Company we host?
> **Domain expert:** Different Customer. Customers don't cross Company lines,
> even with the same email address.
