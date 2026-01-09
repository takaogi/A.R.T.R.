# A.R.T.R. Directory Structure Proposal

Based on the analysis of the design documents and reference projects (Letta, RisuAI), the following directory structure is proposed for the A.R.T.R. project.

## Overview
The structure separates the system into clear **Layers** (Logic flow), **Systems** (State management), and **UI** (Interaction), adhering to the Python project standards observed in Letta.

## Proposed Structure

```text
A.R.T.R/
├── .venv/                      # Virtual Environment (Created)
├── designs/                    # Design Documents (Ignored)
├── run.bat                     # Windows Launcher Script
├── data/                       # Runtime Data & Persistence
│   ├── characters/             # Character Cards (V2 Spec)
│   ├── memories/               # Archival & Core Memory DBs
│   ├── white_room/             # Vision System Target Directory
│   ├── cache/                  # Vision & Preprocessing Caches
│   └── logs/                   # Conversation & Debug Logs
│
├── src/                        # Source Code
│   ├── __init__.py
│   ├── main.py                 # Application Entry Point (Bootstrap)
│   ├── config.py               # Global Settings & Env Loading
│   │
│   ├── schemas/                # Pydantic Models & JSON Schemas (OpenAI Structured Outputs)
│   │   ├── __init__.py
│   │   ├── openai_response.py
│   │   └── tool_schemas.py
│   │
│   ├── ui/                     # User Interface (Tkinter)
│   │   ├── chat_window.py      # Main Chat Interface
│   │   └── components/         # Reusable UI Widgets
│   │
│   ├── layers/                 # Logic Pipeline Layers
│   │   ├── __init__.py
│   │   ├── preprocessor.py     # Sentiment & Intent Analysis
│   │   ├── reflex.py           # Reflex Layer (Fast/Japanese)
│   │   ├── core_thinking.py    # Core Thinking Layer (Deep/English)
│   │   └── translator.py       # Translator Layer (Output Logic)
│   │
│   ├── templates/              # LLM System Prompt Templates (.md/.jinja2)
│   │   ├── system_reflex.md
│   │   ├── system_core.md
│   │   └── system_translator.md
│   │
│   ├── systems/                # Autonomous & State Systems
│   │   ├── emotion/            # VAD & Affection Engine
│   │   ├── pacemaker/          # Autonomous Pulse Generator
│   │   ├── memory/             # Memory Managers (Core, Archival, Recall)
│   │   ├── vision/             # White Room Vision System
│   │   ├── personality/        # Character Card Analyzer & Generators
│   │   └── inner_voice/        # Inner Mind Lifecycle & Persistence
│   │
│   ├── colors/                 # Color.System (Open-Interpreter)
│   │   ├── base_agent.py       # Computer/Tools Interface
│   │   ├── orchestrator.py     # Purple Agent Logic
│   │   └── specialists/        # Blue, Green, Red, Yellow Implementations
│   │
│   └── utils/                  # Shared Utilities
│       ├── llm_client.py       # Unified LLM API Wrapper
│       ├── tools.py            # Function Calling Definitions
│       ├── path_helper.py      # Path resolution for Dev/Frozen (PyInstaller) envs
│       ├── logger.py           # Centralized Logging Setup
│       ├── constants.py        # System Constants & Defaults
│       ├── json_parser.py      # Robust JSON Parsing & Repair
│       └── token_counter.py    # Context Window Management
│
└── tests/                      # Unit & Integration Tests
```

## Rationale
1.  **`src/layers/`**: Directly maps to the `LLM Layer Architecture` design (Reflex -> Core -> Translator).
2.  **`src/systems/`**: Encapsulates the stateful engines (`Emotion`, `Pacemaker`, `Vision`) that run independently or persist across turns.
3.  **`src/colors/`**: Separates the complex Open-Interpreter based sub-agents into their own module, as they are effectively separate entities.
4.  **`data/`**: Keeps user data (Cards, Memories) separate from code, following RisuAI/SillyTavern patterns.
5.  **`ui/`**: Isolates the frontend logic, allowing for potential future replacement (e.g., if switching from Tkinter to a web frontend later) without rewriting core logic.
