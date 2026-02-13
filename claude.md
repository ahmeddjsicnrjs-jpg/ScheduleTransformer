# ScheduleTransformer

Graphical process editor and schedule planner. Combines a node-based graph editor (operations + dependencies) with constraint-based scheduling via Google OR-Tools. Desktop app built with PyQt5.

## Tech Stack

- **Python 3**, **PyQt5** (GUI), **NodeGraphQt** (graph editor), **Google OR-Tools** CP-SAT solver
- OR-Tools solver runs in a **subprocess** (`scheduler_worker.py`) to isolate C++ crashes from the GUI
- All files are in the project root — no package/subdirectory structure

## Project Structure

| File                  | Purpose                                                              |
|-----------------------|----------------------------------------------------------------------|
| `main.py`             | `MainWindow`: menus, toolbar, graph manipulation, save/load, log panel, schedule export, Gantt integration |
| `nodes.py`            | `OperationNode(BaseNode)`: graph node with properties — name, duration (hours/days), workers needed |
| `scheduler.py`        | `build_schedule()`: subprocess wrapper — serializes input as JSON to stdin, reads JSON result from stdout, 60 s timeout |
| `scheduler_worker.py` | OR-Tools CP-SAT model: interval variables, dependency constraints, worker skill matching, no-overlap per worker, makespan minimization |
| `workers_window.py`   | `WorkersWindow(QDialog)`: worker table with name, color picker (`ColorButton`), and operation assignment via autocomplete (`OperationListWidget`). File I/O for workers JSON |
| `gantt_widget.py`     | `GanttCanvas` (custom paint), `GanttWidget` (scrollable dock), `GanttWindow` (fullscreen window, F11 toggle, Esc to close) |
| `requirements.txt`    | Dependencies: `PyQt5>=5.15`, `NodeGraphQt>=0.6`, `ortools>=9.0`     |

## Setup & Run

```bash
pip install -r requirements.txt
python3 main.py
```

## Scheduling Model

- **Time unit**: minutes internally. **1 day = 8 working hours = 480 minutes**
- **Shift**: 8:00–17:00. Display format: `Д1 8:00` (Day 1, 8:00)
- Duration input priority: days field first (×480 min), then hours field (×60 min), fallback 60 min
- **Constraints**: dependency ordering, worker skill matching, no-overlap per worker
- **Objective**: minimize makespan (total project duration)
- **Solver timeout**: 30 s (CP-SAT `max_time_in_seconds`); subprocess timeout: 60 s
- Graph is **acyclic** (`set_acyclic(True)`)

## Data Flow

```
Graph editor (NodeGraphQt) → _extract_graph_data() → operations + dependencies
Workers window → get_workers_data() → workers list
    ↓
scheduler.py → subprocess → scheduler_worker.py (OR-Tools CP-SAT)
    ↓
JSON result → log panel (text table) + GanttWidget (dock) + GanttWindow (fullscreen)
```

## Keyboard Shortcuts

| Shortcut | Action                      |
|----------|-----------------------------|
| Ctrl+N   | Add operation node          |
| Ctrl+S   | Save graph                  |
| Ctrl+O   | Load graph                  |
| Ctrl+R   | Build schedule              |
| Ctrl+Q   | Quit                        |
| Delete   | Delete selected nodes       |
| F11      | Toggle fullscreen Gantt     |
| Esc      | Close fullscreen Gantt      |

## Conventions

- UI language: **Ukrainian** (all labels, tooltips, messages, docstrings)
- Classes: `PascalCase`; methods/functions: `snake_case`; private methods prefixed with `_`
- Section comments with `# --- Section Name ---`
- No automated tests currently
- JSON used for graph serialization (graph + workers bundled) and standalone worker/schedule export; `*.json` files are gitignored
- Global exception handler (`sys.excepthook`) shows `QMessageBox` on unhandled errors
- App style: `Fusion`
