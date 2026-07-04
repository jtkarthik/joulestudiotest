# AR Collection Email Drafting Agent

Personalized collection email generation powered by SAP S/4HANA accounts receivable data.

## Business challenge

Accounts receivable teams spend significant manual effort drafting collection emails for overdue customers. Each email needs to be tailored based on the customer's payment history, open invoice details, and overdue amounts — a time-consuming task prone to inconsistency. An AI agent should automate this by reading live AR data from SAP and generating context-aware, personalized collection emails ready for review and send.

## Key Milestones

1. **Customer AR data retrieved** — open items and payment history fetched from SAP S/4HANA for a given customer.
2. **Payment behavior analyzed** — agent assesses overdue amounts, aging buckets, and prior payment patterns.
3. **Email draft generated** — personalized collection email composed based on the analysis.
4. **Email reviewed by AR specialist** — draft surfaced to a human for approval or edits before sending.
5. **Email dispatched** — final email sent to the customer contact.

## Business Architecture (RBA)

### End-to-End Process

Finance / Invoice to Cash (generic)

### Process Hierarchy

```
Finance (E2E)
└── Invoice to Cash (Phase)
    └── Manage customer invoices (BPS-363)
        └── Invoice customer
    └── Process accounts receivables and collect payment (BPS-366)
        └── Process accounts receivable (AR)
```

### Summary

Drafting personalized collection emails maps to the Invoice to Cash process within Finance — specifically the "Process accounts receivables and collect payment" sub-process, with supporting context from "Manage customer invoices" for invoice-level detail.

## Fit Gap Analysis

| Requirement (business) | Standard asset(s) found | API ORD ID | MCP Server ORD ID | MCP Server Version | Gap? | Notes / assumptions |
| ---------------------- | ----------------------- | ---------- | ----------------- | ------------------ | ---- | ------------------- |
| Retrieve open/overdue invoices per customer | SAP S/4HANA Collections Management (FI-AR) | — | — | — | No | Open item data available via S/4HANA AR APIs |
| Retrieve customer payment history | SAP S/4HANA Customer Payment Collaboration (FI-AR) | — | — | — | No | Payment history accessible via S/4HANA APIs |
| Read dunning/collection status | Contract Accounting Dunning - Read | `sap.s4:apiResource:CADUNNING_0001:v1` | — | — | No | OData API available; no MCP server found |
| Read payment advice details | Payment Advice | `sap.s4:apiResource:CE_PAYMENTADVICE_0001:v1` | — | — | No | OData API available; no MCP server found |
| Generate personalized email content using AI | No standard SAP capability | — | — | — | **Yes** | Custom AI agent required for LLM-based drafting |
| Present draft for human review before sending | No standard SAP capability | — | — | — | **Yes** | Human-in-the-loop step needed in agent workflow |

### Key findings

- SAP S/4HANA provides all required AR data (open items, dunning status, payment history) via standard OData APIs.
- No MCP servers were found for the identified APIs — the agent will call the APIs directly or via a custom MCP translation layer.
- The core gap is the AI-powered email drafting step, which has no standard SAP equivalent and requires a custom agent.
- A human review step is essential before emails are dispatched to avoid erroneous communications.
- The solution combines a structured AR data retrieval workflow with an AI agent for content generation.
- Collections Management (BPS-366) in S/4HANA covers process orchestration; the AI layer adds the personalization capability on top.

## Recommendations

### AI-Powered AR Collection Email Drafting Agent

#### Executive Summary

Python AI agent reads S/4HANA AR data and drafts personalized collection emails.

#### Recommended Solution

A Python-based AI agent (A2A protocol) integrated with SAP S/4HANA via standard OData APIs. The agent retrieves open items, payment history, and dunning status for a given customer, analyzes the data to determine tone and urgency, and generates a personalized collection email draft. The draft is surfaced to an AR specialist for review before dispatch. The agent runs on SAP BTP AI Core.

#### Recommended solution category

AI Agent

#### Intent fit
90%
