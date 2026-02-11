"""
Модуль планування розкладу на основі Google OR-Tools CP-SAT Solver.

Приймає граф операцій (з залежностями) та список працівників,
будує оптимальний розклад з урахуванням:
  - тривалості кожної операції
  - кількості необхідних працівників
  - залежностей між операціями
  - кваліфікації працівників (які операції вони можуть виконувати)
"""

from ortools.sat.python import cp_model


def build_schedule(operations: list[dict],
                   dependencies: list[tuple[str, str]],
                   workers: list[dict]) -> dict | None:
    """
    Побудувати розклад.

    Parameters
    ----------
    operations : list[dict]
        Кожен елемент: {'id': str, 'name': str, 'duration': int, 'workers_needed': int}
    dependencies : list[tuple[str, str]]
        Пари (id_попередника, id_наступника). Наступник не може початися
        поки попередник не завершиться.
    workers : list[dict]
        Кожен елемент: {'name': str, 'operations': [str, ...]}
        operations — список НАЗВ операцій, які працівник може виконувати.

    Returns
    -------
    dict | None
        {'makespan': int,
         'assignments': [{'operation_id': str, 'operation_name': str,
                          'start': int, 'end': int,
                          'workers': [str, ...]}, ...]}
        або None якщо розклад неможливий.
    """
    if not operations:
        return {'makespan': 0, 'assignments': []}

    model = cp_model.CpModel()

    # Максимальний горизонт — сума всіх тривалостей (верхня межа)
    horizon = sum(op['duration'] for op in operations)

    op_by_id = {op['id']: op for op in operations}
    op_name_by_id = {op['id']: op['name'] for op in operations}

    # --- Змінні для кожної операції ---
    starts = {}
    ends = {}
    intervals = {}

    for op in operations:
        oid = op['id']
        dur = op['duration']
        s = model.new_int_var(0, horizon, f'start_{oid}')
        e = model.new_int_var(0, horizon, f'end_{oid}')
        iv = model.new_interval_var(s, dur, e, f'interval_{oid}')
        starts[oid] = s
        ends[oid] = e
        intervals[oid] = iv

    # --- Обмеження залежностей ---
    for pred_id, succ_id in dependencies:
        if pred_id in ends and succ_id in starts:
            model.add(starts[succ_id] >= ends[pred_id])

    # --- Призначення працівників ---
    # Для кожної пари (працівник, операція) створюємо булеву змінну
    assign_vars = {}  # (worker_idx, op_id) -> BoolVar
    worker_intervals = {w_idx: [] for w_idx in range(len(workers))}

    for op in operations:
        oid = op['id']
        op_name = op['name']
        needed = op['workers_needed']

        # Знайти працівників, які можуть виконувати цю операцію
        capable_workers = []
        for w_idx, w in enumerate(workers):
            if op_name in w.get('operations', []):
                capable_workers.append(w_idx)

        if len(capable_workers) < needed:
            # Недостатньо кваліфікованих працівників
            return None

        # Булеві змінні призначення
        op_assign_vars = []
        for w_idx in capable_workers:
            var = model.new_bool_var(f'assign_w{w_idx}_op{oid}')
            assign_vars[(w_idx, oid)] = var
            op_assign_vars.append(var)

            # Якщо працівник призначений — він зайнятий на цей інтервал
            opt_interval = model.new_optional_interval_var(
                starts[oid], op['duration'], ends[oid],
                var, f'worker_interval_w{w_idx}_op{oid}'
            )
            worker_intervals[w_idx].append(opt_interval)

        # Рівно `needed` працівників мають бути призначені
        model.add(sum(op_assign_vars) == needed)

    # --- Кожен працівник не може виконувати дві операції одночасно ---
    for w_idx in range(len(workers)):
        if worker_intervals[w_idx]:
            model.add_no_overlap(worker_intervals[w_idx])

    # --- Мінімізуємо makespan ---
    makespan = model.new_int_var(0, horizon, 'makespan')
    for op in operations:
        model.add(makespan >= ends[op['id']])
    model.minimize(makespan)

    # --- Розв'язати ---
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0
    status = solver.solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    # --- Зібрати результати ---
    assignments = []
    for op in operations:
        oid = op['id']
        assigned_workers = []
        for w_idx, w in enumerate(workers):
            key = (w_idx, oid)
            if key in assign_vars and solver.value(assign_vars[key]):
                assigned_workers.append(w['name'])

        assignments.append({
            'operation_id': oid,
            'operation_name': op['name'],
            'start': solver.value(starts[oid]),
            'end': solver.value(ends[oid]),
            'duration': op['duration'],
            'workers': assigned_workers,
        })

    assignments.sort(key=lambda a: (a['start'], a['operation_name']))

    return {
        'makespan': solver.value(makespan),
        'assignments': assignments,
    }
