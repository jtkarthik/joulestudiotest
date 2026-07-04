---
name: collection-email-drafting
description: Provides tone guidelines and email templates for drafting collection emails based on customer payment risk tier
---

# Collection Email Drafting Skill

This skill provides email tone calibration and template patterns for drafting collection emails
based on SAP S/4HANA Accounts Receivable data.

## Tone Guidelines by Risk Tier

### Low Risk (friendly)
- Use a polite, helpful tone
- Assume the oversight was unintentional
- Offer easy payment options
- Example opening: "We hope this message finds you well. We wanted to bring to your attention..."

### Medium Risk (firm)
- Use a professional, direct tone
- Reference specific invoice numbers and due dates
- Include a clear deadline for response
- Example opening: "This is a reminder that the following invoices remain outstanding..."

### High Risk (urgent)
- Use an assertive, time-sensitive tone
- Mention potential service disruption or account review
- Request immediate contact or payment
- Example opening: "URGENT: Your account has significant overdue balances requiring immediate attention..."

### Critical Risk (legal)
- Use a formal tone with legal weight
- Reference escalation to collections department
- Include a final deadline before legal action
- Example opening: "FINAL NOTICE: Despite prior communications, the following amounts remain unpaid..."

## Email Structure Template

```
Subject: [TONE-APPROPRIATE SUBJECT] – Invoice [#] / Account [ID]

Dear [Customer Name / Accounts Payable Team],

[OPENING PARAGRAPH — reference the relationship and purpose]

[INVOICE TABLE — Invoice #, Amount, Due Date, Days Overdue]

[ACTION PARAGRAPH — what the customer needs to do and by when]

[CONTACT PARAGRAPH — who to contact with questions]

[CLOSING]

Best regards / Sincerely / Regards,
[Your Name]
[Title]
[Company AR Team]
[Phone / Email]
```

## Key Rules
- Always use exact invoice numbers, amounts, and dates from SAP data
- Never invent or estimate financial figures
- Include currency codes with all amounts
- End every email draft with: "Please review and send this draft if it meets your requirements."
- Do not include payment gateway links or bank account details (those must be added by the human reviewer)
