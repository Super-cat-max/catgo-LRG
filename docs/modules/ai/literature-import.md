---
title: Paper Import
description: PDF and DOI ingestion for paper-grounded conversations
source: server/catgo/routers/paper.py
---

# Paper Import

**Source:** `server/catgo/routers/paper.py`, `server/catgo/models/paper.py`

The paper import module ingests scientific papers into CatGo's session store so CatBot can reference them while constructing workflows. Two ingestion paths are supported: direct PDF upload, and DOI resolution via CrossRef metadata.

This module is the data ingestion layer. The downstream "tell CatBot about this paper and let it build a workflow" flow happens through normal CatBot chat turns — there is no automated paper-to-workflow extractor.

## What This Module Does

- **PDF upload** — Accept a PDF, extract its text content, store it in a TTL-managed session
- **DOI resolution** — Resolve a DOI through CrossRef to get title, authors, abstract, and metadata
- **Session storage** — Hold paper text + metadata in memory keyed by session ID, with automatic cleanup after a TTL window
- **Text retrieval** — Return the extracted text for chat context augmentation

## What This Module Does *Not* Do

- Automatic parameter extraction (functionals, k-points, cutoffs) from paper PDFs — this is a CatBot prompt-driven task, not a backend feature
- Automatic workflow generation from paper methods — users describe the paper's method in chat and let CatBot construct the workflow

## Server API

All endpoints live under the `/paper` prefix:

| Endpoint | Method | Description |
|---|---|---|
| `/paper/upload` | `POST` | Upload a PDF; returns a `session_id` and parsed metadata |
| `/paper/{session_id}` | `GET` | Retrieve session info (title, authors, page count, expiry) |
| `/paper/{session_id}/text` | `GET` | Get the extracted text body of the paper |
| `/paper/resolve-doi` | `POST` | Resolve a DOI via CrossRef; returns metadata without storing |
| `/paper/{session_id}` | `DELETE` | Manually clean up a session before TTL expiry |

## Data Model

### `PaperSessionInfo`

- `session_id` — UUID for the in-memory session
- `title` — Paper title (from PDF metadata or first heading)
- `authors` — Author list (when extractable)
- `created_at` — Session creation timestamp
- `expires_at` — TTL expiry timestamp

### `DOIResolveResponse`

Returns CrossRef metadata: title, authors, journal, publication year, abstract, and the resolved DOI URL.

## Typical Flow

1. User drops a PDF into CatBot or pastes a DOI
2. Frontend posts to `/paper/upload` or `/paper/resolve-doi` and receives a `session_id`
3. The chat context includes the paper's text/metadata in subsequent LLM calls (see [`context.ts`](/modules/ai/chat-system))
4. User asks CatBot to build a workflow based on the paper's method — CatBot drafts the workflow via the [workflow tools](/modules/ai/workflow-tools)
5. Session expires after TTL or is manually deleted

## Related

- [Paper Import Tutorial](/tutorials/ai/literature-import) — Step-by-step user guide
- [Chat System](/modules/ai/chat-system) — How paper context flows into LLM calls
- [Workflow Tools](/modules/ai/workflow-tools) — The tools CatBot uses to construct workflows
