# Skill: Corporate Knowledge Retrieval

## Tool: `lookup_company_policy`
Use this skill when the user asks about ANY internal company topic (HR, IT, Projects, Pricing).

## Query Strategy (CRITICAL)
The search engine matches keywords. You must translate user intent into "Handbook Language".

| User Says | You Search For |
| :--- | :--- |
| "wifi sucks" | "corporate wireless network troubleshooting" |
| "I need a break" | "mental health leave policy" |
| "vpn key" | "AcmeGuard VPN shared secret" |

## Usage Rules
1. **Search First:** Never answer policy questions from your own training data. ALWAYS use `lookup_company_policy` first.
2. **Cite Sources:** If the tool returns a document name (e.g., `HR_01.md`), mention it in your answer.
3. **Refusal:** If the tool returns "No documents found," apologize and state you cannot find that information. Do NOT make it up.
