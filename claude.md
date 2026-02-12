# ScheduleTransformer

Graphical process editor and schedule planner. Combines a node-based graph editor (operations + dependencies) with constraint-based scheduling via Google OR-Tools. Desktop app built with PyQt5.

## Tech Stack

- **Python 3**, **PyQt5** (GUI), **NodeGraphQt** (graph editor), **Google OR-Tools** (CP solver)
- OR-Tools solver runs in a **subprocess** (`scheduler_worker.py`) to isolate crashes from the GUI

## Project Structure

| File                  | Purpose                                      |
|-----------------------|----------------------------------------------|
| `main.py`             | Main window, menus, toolbar, graph manipulation |
| `nodes.py`            | OperationNode class for graph nodes          |
| `scheduler.py`        | Subprocess wrapper for the solver            |
| `scheduler_worker.py` | OR-Tools constraint model and solver logic   |
| `workers_window.py`   | Worker management dialog                     |
| `gantt_widget.py`     | Gantt chart visualization widget             |

## Setup & Run

```bash
pip install -r requirements.txt
python3 main.py
```

## Conventions

- UI language: **Ukrainian**
- Classes: `PascalCase`; methods: `snake_case`; private methods prefixed with `_`
- Section comments with `# --- Section Name ---`
- No automated tests currently
- JSON used for graph serialization and worker data; `.json` files are gitignored
