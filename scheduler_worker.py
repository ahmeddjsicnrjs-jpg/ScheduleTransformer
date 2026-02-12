"""
Окремий процес для запуску OR-Tools solver.
Читає JSON зі stdin, виводить результат у stdout.
Якщо solver крешне — впаде тільки цей процес, а не GUI.
"""

import sys
import json

from ortools.sat.python import cp_model


def build_schedule(operations, dependencies, workers):
    if not operations:
        return {'makespan': 0, 'assignments': []}

    model = cp_model.CpModel()

    horizon = sum(int(op['duration']) for op in operations)

    starts = {}
    ends = {}
    intervals = {}

    for op in operations:
        oid = op['id']
        dur = int(op['duration'])
        s = model.new_int_var(0, horizon, 'start_%s' % oid)
        e = model.new_int_var(0, horizon, 'end_%s' % oid)
        iv = model.new_interval_var(s, dur, e, 'interval_%s' % oid)
        starts[oid] = s
        ends[oid] = e
        intervals[oid] = iv

    for pred_id, succ_id in dependencies:
        if pred_id in ends and succ_id in starts:
            model.add(starts[succ_id] >= ends[pred_id])

    assign_vars = {}
    worker_intervals = {}
    for w_idx in range(len(workers)):
        worker_intervals[w_idx] = []

    for op in operations:
        oid = op['id']
        op_name = op['name']
        needed = int(op['workers_needed'])

        capable_workers = []
        for w_idx, w in enumerate(workers):
            if op_name in w.get('operations', []):
                capable_workers.append(w_idx)

        if len(capable_workers) < needed:
            return None

        op_assign_vars = []
        for w_idx in capable_workers:
            var = model.new_bool_var('assign_w%d_op%s' % (w_idx, oid))
            assign_vars[(w_idx, oid)] = var
            op_assign_vars.append(var)

            opt_interval = model.new_optional_interval_var(
                starts[oid], int(op['duration']), ends[oid],
                var, 'worker_interval_w%d_op%s' % (w_idx, oid)
            )
            worker_intervals[w_idx].append(opt_interval)

        model.add(sum(op_assign_vars) == needed)

    for w_idx in range(len(workers)):
        if worker_intervals[w_idx]:
            model.add_no_overlap(worker_intervals[w_idx])

    makespan = model.new_int_var(0, horizon, 'makespan')
    for op in operations:
        model.add(makespan >= ends[op['id']])
    model.minimize(makespan)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0
    status = solver.solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    assignments = []
    for op in operations:
        oid = op['id']
        assigned_workers = []
        for w_idx, w in enumerate(workers):
            key = (w_idx, oid)
            if key in assign_vars and solver.value(assign_vars[key]):
                assigned_workers.append(w['name'])

        dur_min = int(op['duration'])
        assignments.append({
            'operation_id': oid,
            'operation_name': op['name'],
            'start': solver.value(starts[oid]),
            'end': solver.value(ends[oid]),
            'duration': dur_min,
            'duration_hours': round(dur_min / 60, 2),
            'workers': assigned_workers,
        })

    assignments.sort(key=lambda x: (x['start'], x['operation_name']))

    ms = solver.value(makespan)
    return {
        'makespan': ms,
        'makespan_hours': round(ms / 60, 2),
        'assignments': assignments,
    }


if __name__ == '__main__':
    try:
        input_data = json.loads(sys.stdin.read())
        result = build_schedule(
            input_data['operations'],
            [tuple(d) for d in input_data['dependencies']],
            input_data['workers'],
        )
        print(json.dumps({'ok': True, 'result': result}, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({'ok': False, 'error': str(e)}, ensure_ascii=False))
