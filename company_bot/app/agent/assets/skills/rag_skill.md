# Skill: Corporate Knowledge Retrieval

## Tool: `lookup_company_policy`
Use this skill for ANY inquiry regarding Acme Corp internal documentation.

## Query Strategy: "Handbook Language"
The database is keyword-sensitive. You must translate user intent into formal search terms before calling the tool.

| User Intent | Expanded Search Query |
| :--- | :--- |
| "wifi/internet" | "corporate wireless network configuration and passwords" |
| "vacation/time off" | "HR employee paid time off and vacation policy" |
| "vpn access" | "AcmeGuard VPN configuration and shared secret" |
| "pricing" | "Sales subscription pricing strategy and effective dates" |

## Execution Protocol
1. **Silent Execution:** Run the tool immediately. Do not announce it.
2. **Search First:** Never answer from your own training data; always query the database.
3. **Citation:** Always mention the filename of the document found.
4. **Failure:** If no results are found, revert to the Refusal Protocol in AGENTS.md.
