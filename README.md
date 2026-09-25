# ZeroTouch AI: Zero-Ticket Proactive Resolution

**The Pitch:** Customer support for consumer payments shouldn't be about closing tickets faster—it should be about *tickets avoided*. Transaction-failure volume (e.g., money debited, merchant not credited) is a massive support driver for platforms like Paytm. 

ZeroTouch is an autonomous AI teammate that proactively investigates and resolves these failures before the customer even needs to reach out.

## The Mechanics

A "reconciliation watcher" continuously ingests transaction events. When a transaction lands in a failure or ambiguous state, the AI teammate springs into action:

1. **Cross-checks Data:** Gathers evidence across Bank, Network (NPCI), Merchant, and Settlement ledgers (mocked as distinct APIs/datasets for this prototype).
2. **AI Investigation:** An LLM agent (powered by Gemini) reasons over the evidence to classify the transaction and generate a clear investigation narrative.
3. **Classifies & Acts:** 
   - **Clear-cut (Auto-Resolve):** Auto-initiates a refund, proactively messages the user with status + ETA, and closes the loop. **No ticket ever created.**
   - **Ambiguous (Human Escalation):** Creates a ticket that is *already pre-investigated*, with all logs attached and a draft resolution suggested, making human escalation vastly faster.

The escalation logic is the centerpiece of this demo: showing the AI teammate correctly separating "auto-resolve" from "needs human" cases live.

*(Note for Hackathon Judges: To keep this prototype self-contained, the reconciliation data is mocked. In a production environment, this data would be ingested via bank webhooks and NPCI settlement files.)*

---

## Test Scenarios

The prototype mocks three specific scenarios to demonstrate the platform's decision-making capabilities:
* **TX9281 (Clear-cut Auto-Reversal):** A low-risk payment where the customer was debited but the merchant was not credited. The system safely executes an autonomous reversal.
* **TX9342 (Ambiguous Escalation):** A high-risk, high-value transaction with conflicting network states. The system safely halts and escalates to a human agent, providing the investigation narrative as context.
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
