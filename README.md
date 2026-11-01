# 🏭 AI Warehouse Control System

**Talk to a simulated warehouse in plain English. The AI proposes, a deterministic safety layer decides.**

An MCP (Model Context Protocol) server connects an AI agent (Claude Desktop) to a fleet of simulated warehouse robots. Every command the AI sends passes through a rule-based **Safety Validator** before it can touch the simulation, and every decision is logged. It runs entirely on a laptop, with no hardware needed.

<!-- DEMO VIDEO: edit this README on github.com, drag docs/demo.mp4 into the editor right here. GitHub uploads it and inserts a player link on its own line. Then delete this comment. -->

> A natural-language command goes through the MCP tools and the safety validator, and the robot moves on the live dashboard.

---

## 💡 Why this project exists

Giving an LLM control over anything real is risky: it can hallucinate a robot ID, ignore a low battery, or loop on a command. This project explores one answer to that problem:

> **The LLM never mutates system state directly.** It can only call a small set of MCP tools, and each state-changing call is independently validated by plain, testable code.

It started as inspiration from a physical ESP32 warehouse robot I built for a college project. I rebuilt the idea as a pure-software system so it can be developed, tested and demoed without any hardware.

---

## 🎬 See it in action

| Live dashboard | Claude checks live state first and catches an invalid robot (R5) |
|:---:|:---:|
| ![Dashboard](docs/dashboard.png) | ![Invalid robot caught](docs/invalid_robot.png) |

| ML risk prediction before assigning a task | Audit trail of every AI action |
|:---:|:---:|
| ![Risk prediction](docs/risk_prediction.png) | ![Audit log](docs/audit_log.png) |

---

## 🧩 Architecture

![Architecture Diagram](docs/architecture.png)

**How a command flows:**

1. You ask Claude Desktop something in natural language.
2. Claude picks an MCP tool (for example `assign_task`) and fills in the arguments.
3. The **Safety Validator** checks the command against deterministic rules. If it fails, the agent gets a clear rejection reason.
4. Only approved commands reach the **Simulation Engine**, which updates robots every tick.
5. Every tick (telemetry) and every AI decision (audit log) is written to **SQLite**.
6. The **dashboard** and **analytics notebook** read from the same database, and the **ML model** estimates failure risk before a task is assigned.

---

## ✨ Features

- **Natural-language control** via 10 MCP tools (status, layout, task assignment, emergency stop, reset, history, telemetry, audit log, risk prediction)
- **Deterministic Safety Validator** with these rules:
  - unknown robot or zone rejection
  - robots in `FAULT` / `EMERGENCY_STOPPED` / busy states can't take tasks
  - low-battery rejection (single shared threshold constant)
  - per-robot rate limiting
  - `emergency_stop` always allowed and never rate-limited
- **Simulated robot fleet** (3 robots) with a full state machine: `IDLE → MOVING → DELIVERING → CHARGING`, plus `FAULT` and `EMERGENCY_STOPPED`
- **Seeded, deterministic simulation** for reproducible tests (randomness and time are injected, not hardcoded)
- **Full audit trail**: every tool call, approval or rejection, and reason is stored
- **Live Streamlit dashboard** with a warehouse map, robot status and AI action log
- **Analytics notebook** covering utilization, battery trends, task success rate and completion-time distribution
- **ML risk predictor** exposed as its own MCP tool

---

## 🧠 Machine Learning: task failure risk

A Logistic Regression model estimates the probability that a task will fail *before* it is assigned.

| Model | Macro F1 | Accuracy |
|---|---|---|
| Baseline (always predict majority class) | 0.41 | 0.69 |
| **Logistic Regression** (selected) | **0.62** | 0.67 |
| Random Forest (max_depth=5) | 0.57 | 0.62 |

- Used a **time-based train/test split** to avoid leaking future tasks into training
- Chose **macro F1 over accuracy** because the classes are imbalanced, and the baseline's higher accuracy is misleading (it never predicts a failure)
- Route distance and starting battery were the most important features
- **Honest limitation:** failures in the simulation are partly random by design, so predictive power is modest. The tool's response says so explicitly and compares each prediction to the dataset's average failure rate.

Full methodology: [`analytics/MODEL_CARD.md`](analytics/MODEL_CARD.md)

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python |
| MCP server | FastMCP |
| Database | SQLite |
| Dashboard | Streamlit + Matplotlib |
| Analytics | Pandas + Plotly + Jupyter |
| ML | scikit-learn + joblib |
| Testing | pytest + pytest-asyncio |

---

## 📁 Project Structure

```
ai_warehouse_mcp/
├── simulation/     # Robot, Warehouse, Task models + tick-based engine
├── safety/         # Safety Validator (testable with no MCP or hardware)
├── mcp_server/     # FastMCP app wiring validator + engine + database
├── storage/        # SQLite persistence (telemetry, audit log)
├── dashboard/      # Streamlit live view
├── analytics/      # Data generation, EDA notebook, ML notebook, model card
├── tests/          # automated tests across every layer
├── config/         # shared constants (battery threshold, grid size, ...)
├── docs/           # demo GIF, screenshots, architecture diagram
└── run_server.bat  # entry point used by Claude Desktop (Windows)
```

---

## 🚀 Getting Started

**Prerequisites:** Python 3.10+, Claude Desktop

```powershell
git clone <your-repo-url>
cd ai_warehouse_mcp

python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

pytest -v
```

### Connect to Claude Desktop

Add this to `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ai-warehouse-mcp": {
      "command": "C:\\path\\to\\ai_warehouse_mcp\\run_server.bat"
    }
  }
}
```

Fully quit and restart Claude Desktop, then try:

- *"What zones exist in this warehouse?"*
- *"What's the risk of sending R2 from Storage to Dispatch?"*
- *"Move R1 from Pickup to Dispatch"*
- *"Assign a task to robot R99"* (watch the validator reject it)
- *"Emergency stop R3"*, then *"Reset R3"*

### Run the dashboard

In a separate terminal, with the venv active:

```powershell
streamlit run dashboard/app.py
```

> Let Claude Desktop start the server. Starting `run_server.bat` manually at the same time creates two simulation instances writing to the same database.

### Generate analytics data and retrain the model

```powershell
python analytics/generate_sample_data.py
jupyter notebook analytics/ml_model.ipynb
```

---

## 🧪 Testing approach

- The Safety Validator and Simulation Engine are tested **independently** of each other and of MCP.
- Randomness (`rng`) and time (`clock`) are **injected dependencies**, so fault injection and rate limiting are tested deterministically, with no `sleep` and no flaky tests.
- MCP tools are tested through FastMCP's in-memory `Client`, covering tool discovery, schema, call and response without a subprocess.

---

## ⚠️ Known Limitations

Being upfront about what this MVP does *not* do:

- Robots charge **in place** when the battery is low, instead of navigating to the Charging zone.
- Movement is simple step-by-step toward the target, with no pathfinding or collision avoidance.
- `reset_robot` is callable by the AI for demo purposes. In production it should require human approval.
- A single-instance file lock exists (`storage/lock.py`) but is not yet wired into the server entry point.
- The ML model is trained on simulated data, so it demonstrates the workflow, not real-world accuracy.

---

## 🔮 Future Work

- Navigate to the Charging zone, plus A* pathfinding and multi-robot collision avoidance
- Human-in-the-loop approval for `reset_robot`
- Wire up the singleton lock at server startup
- WebSocket-based dashboard updates instead of polling
- Persistent DB connection / WAL mode for higher telemetry write throughput
- More models (for example gradient boosting) as telemetry grows

---

## 📄 License

MIT. See [LICENSE](LICENSE).
