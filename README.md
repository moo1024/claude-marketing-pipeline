# claude-marketing-pipeline

A six-agent content pipeline built on [Claude Code](https://claude.com/claude-code) subagents.
It turns an event agency's project records — Notion databases, final reports, PDFs, loose photos —
into publishable writing, and refuses to publish anything that fails review.

The goal was never "automate blogging." It was to stop a company's delivered work from
disappearing into a folder nobody reopens.

---

## Pipeline

```
source material  →  archive  →  draft  →  4-axis review  →  channel format  →  human publishes
                       │          │            │                   │                  │
              notion-archive-  marketing-  content-editor-   channel-           (no agent
                  manager      content-      reviewer        distributor         has this)
                                writer      80-pt gate
```

| Agent | Responsibility |
|---|---|
| `marketing-orchestrator` | Single entry point; sequences the run |
| `notion-archive-manager` | Raw material (PDF / notes / DB rows) → structured Notion archive |
| `marketing-content-writer` | Archive → blog draft + reusable assets |
| `content-editor-reviewer` | Scores on SEO, factual accuracy, brand tone, readability |
| `channel-distributor` | Approved draft → Naver Blog format |
| `sns-distributor` | Approved draft → social card format |

One command runs the whole thing:

```bash
/run-blog-pipeline [input]              # full pipeline
/run-blog-pipeline [input] --stage N    # resume from a stage
```

Or step by step: `/archive-from-pdf` → `/blog-from-archive` → `/blog-review` → `/channel-distribute`

## Two design decisions worth explaining

**The reviewer is a different agent from the writer.** An agent asked to check its own draft finds
it acceptable. Separating them means the review has something to actually reject. Drafts scoring
under 80 across the four axes go back rather than forward.

**No agent can publish.** Every channel step ends at a formatted draft. The publish button is
pressed by a person. The same rule covers destructive Notion operations — deleting, moving, or
changing database structure all require explicit approval, and the agents have no standing
permission for any of it.

`scripts/fact_audit.py` exists for the same reason: generated copy that cites a number gets the
number checked against the archive it came from, not against the model's memory.

## Layout

```
.claude/agents/     agent definitions (6)
.claude/commands/   slash commands (9)
.claude/rules/      tone, format, review criteria, MCP safety (7)
docs/               pipeline state, DB schema, observed winning patterns
scripts/            scoring, fact audit, channel publishing
```

## Status

Running in production for a Korean event agency. `docs/PIPELINE_STATE.md` tracks what has been
through the pipeline, including the cases where stage 1 could not be reconstructed retroactively.
