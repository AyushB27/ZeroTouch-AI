# Paytm Refund & Settlement Policy (Internal)

## 1. Failed or Stuck Payment Resolution (Workflow 1)
When a customer's bank account is debited but the merchant's ledger does not show a credit, the transaction is considered in an ambiguous state.

**Rule 1.1: Auto-Reversal Thresholds**
An autonomous agent MAY automatically initiate a reversal to the customer if ALL of the following are true:
- The payment network confirms success, but the merchant ledger confirms no credit.
- The settlement system shows no record of settlement (NOT_FOUND).
- The transaction amount is less than or equal to ₹5,000.
- The user's risk score is less than 0.40.
- There is no previous refund associated with this transaction ID.

**Rule 1.2: Human Escalation Triggers**
An autonomous agent MUST NOT execute an action and MUST escalate to human review if ANY of the following occur:
- Conflicting sources (e.g., Network says FAILED, but Bank says DEBITED).
- The network or settlement status is UNKNOWN or timed out.
- The risk score is between 0.40 and 0.85 (High Risk).
- The transaction amount exceeds ₹5,000.
- A previous refund was already initiated (to prevent double-refunds).

**Rule 1.3: Duplicate Debit Prevention**
If two debits occur for the exact same amount to the exact same merchant within 60 seconds of each other, reverse the duplicate only, keeping the original credited transaction.

## 2. Refund Tracking and SLA Chasing (Workflow 2)
When a refund is initiated, it has a strict SLA window.

**Rule 2.1: Inside SLA**
If the refund is within the 5-day window and the bank has acknowledged it, monitor only. No action required.

**Rule 2.2: SLA Breached (Bank Acknowledged)**
If the refund is past 5 days and the bank has acknowledged it but the customer has not received it, the agent should auto-chase the bank through the escalation API.

## 3. Merchant Settlement Mismatch (Workflow 3)
When a merchant settlement batch is less than the expected ledger amount.

**Rule 3.1: Fees and Deductions**
Explainable gaps (like standard platform fees, GST, or netted refunds) do not require escalation. An itemized explanation can be generated and sent to the merchant.
