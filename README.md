# ZeroTouch AI Prototype

## Setup

1. Install backend dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

2. Start backend server:
   ```bash
   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```

3. Install frontend dependencies:
   ```bash
   cd frontend
   npm install
   ```

4. Start frontend server:
   ```bash
   npm run dev
   ```
