---
name: rag-knowledge
description: Use the internal RAG tool to answer Acme Corp questions by searching company docs and citing sources.
---

# Acme RAG Knowledge

Use this skill for any question about Acme Corp policies, benefits, IT, engineering standards, security, projects, or pricing.

## When to Use
- The user asks about Acme Corp rules, policies, procedures, projects, or internal facts.
- The user references internal docs or wants “the official answer.”

## Tools
- `lookup_company_policy`

## Workflow
1. Translate the user request into a formal, doc-like query (use key nouns, official terms).
2. Call `lookup_company_policy` once with the refined query.
3. Answer using only the returned snippets.
4. Cite the source filename and header path from the snippet.
5. If results are empty or irrelevant, say you couldn’t find it in internal docs and ask a targeted follow‑up question.

## Query Examples
| User intent | Query to send |
| --- | --- |
| “vpn access” | “AcmeGuard VPN configuration and shared secret” |
| “vacation / time off” | “HR employee paid time off and vacation policy” |
| “pricing tiers” | “Sales subscription pricing strategy and tier features” |
| “project chimera status” | “Project Chimera beta status and performance thresholds” |
