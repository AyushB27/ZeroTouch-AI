# ZeroTouch AI Prototype

ZeroTouch is an autonomous payment resolution prototype that demonstrates how AI can investigate and resolve failed or anomalous payments without manual human intervention or support tickets.

## The Core Concept

When a payment goes wrong, the ZeroTouch platform follows a structured, autonomous workflow:
1. **Data Ingestion & Reconciliation:** Pulls transaction data across the Bank, Payment Network, Merchant Ledger, and Settlement systems.
2. **AI Investigation:** An LLM agent (powered by Gemini) reasons over the evidence to generate a coherent investigation narrative. 
3. **Policy Engine:** A strict, deterministic rules engine decides the outcome based on risk scores, amount thresholds, and system states (never relying on the LLM to authorize financial actions).
4. **Action & Verification:** Safely executes permitted actions (like an auto-reversal), independently verifies the outcome, and notifies the customer—all automatically. High-risk or highly ambiguous cases are safely escalated to a human.

## Test Scenarios

The prototype mocks three specific scenarios to demonstrate the platform's decision-making capabilities:
* **TX9281 (Auto Resolution):** A low-risk payment where the customer was debited but the merchant was not credited. The system safely executes an autonomous reversal.
* **TX9342 (Human Escalation):** A high-risk, high-value transaction with conflicting network states. The system safely halts and escalates to a human agent, providing the investigation narrative as context.
* **TX9410 (No Action):** A successfully settled and consistent transaction across all 4 ledgers. No action is taken.

---

## Running the Prototype locally

You will need two terminal windows to run both the FastAPI backend and the React frontend.

### 1. Backend Setup (FastAPI)
The backend manages the orchestration, AI reasoning, policy engine, and simulated ledgers.

1. Create a `.env` file inside the `backend/` directory and add your Gemini API key (see `backend/.env.example`).
   ```env
   GEMINI_API_KEY=your_api_key_here
   ```
2. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. Start the backend server (from the root directory):
   ```bash
   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```

### 2. Frontend Setup (React/Vite)
The frontend provides a real-time visualization of the agent's timeline, the generated narrative, and the final resolution.

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the frontend development server:
   ```bash
   npm run dev
   ```
4. Open the displayed `localhost` URL (usually `http://localhost:3000` or `5173`) in your browser to interact with the dashboard.
