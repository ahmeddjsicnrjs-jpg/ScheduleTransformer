"""
Модуль планування розкладу — запускає OR-Tools в окремому процесі,
щоб C++ crash не вбивав GUI.
"""

import sys
import os
import json
import subprocess


def build_schedule(operations, dependencies, workers):
    """
    Побудувати розклад, запустивши solver у окремому subprocess.

    Returns dict or None.
    """
    if not operations:
        return {'makespan': 0, 'assignments': []}

    input_data = json.dumps({
        'operations': operations,
        'dependencies': dependencies,
        'workers': workers,
    }, ensure_ascii=False)

    worker_script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 'scheduler_worker.py')

    try:
        proc = subprocess.run(
            [sys.executable, worker_script],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return None

    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        raise RuntimeError(
            'Solver process crashed (exit code %d).\n%s' % (proc.returncode, stderr)
        )

    if not proc.stdout.strip():
        raise RuntimeError('Solver process returned empty output.\nstderr: %s' % proc.stderr)

    response = json.loads(proc.stdout)
    if not response.get('ok'):
        raise RuntimeError('Solver error: %s' % response.get('error', 'unknown'))

    return response.get('result')
