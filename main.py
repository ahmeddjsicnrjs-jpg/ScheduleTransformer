#!/usr/bin/env python3
"""
ScheduleTransformer — графічний редактор процесів із плануванням розкладу.

Використовує NodeGraphQt для графічного представлення операцій та
Google OR-Tools для оптимального планування розкладу.
"""

import sys
import json
import traceback

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QDockWidget, QAction, QToolBar,
    QFileDialog, QMessageBox, QWidget, QVBoxLayout, QTextEdit,
)
from PyQt5.QtCore import Qt

from NodeGraphQt import NodeGraph, PropertiesBinWidget

from nodes import OperationNode
from workers_window import WorkersWindow
from scheduler import build_schedule


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('ScheduleTransformer — Редактор процесів')
        self.setMinimumSize(1100, 700)
        self._last_schedule = None

        # --- Node Graph ---
        self._graph = NodeGraph()
        self._graph.set_acyclic(True)
        self._graph.register_node(OperationNode)

        graph_widget = self._graph.widget
        self.setCentralWidget(graph_widget)

        # --- Properties panel (dock) ---
        self._properties_bin = PropertiesBinWidget(node_graph=self._graph)
        props_dock = QDockWidget('Властивості вузла')
        props_dock.setWidget(self._properties_bin)
        self.addDockWidget(Qt.RightDockWidgetArea, props_dock)

        # --- Log / results panel (dock, bottom) ---
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        log_dock = QDockWidget('Журнал / Результати')
        log_dock.setWidget(self._log)
        self.addDockWidget(Qt.BottomDockWidgetArea, log_dock)

        # --- Workers window ---
        self._workers_window = WorkersWindow(self)

        # --- Toolbar ---
        self._create_toolbar()

        # --- Menu ---
        self._create_menu()

        self._log_msg('Програму запущено. Додайте операції через панель або Ctrl+N.')

    # ------------------------------------------------------------------
    # UI Setup
    # ------------------------------------------------------------------

    def _create_toolbar(self):
        toolbar = QToolBar('Головна')
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        act_add_node = QAction('+ Операція', self)
        act_add_node.setToolTip('Додати нову операцію')
        act_add_node.triggered.connect(self._add_operation_node)
        toolbar.addAction(act_add_node)

        toolbar.addSeparator()

        act_workers = QAction('Працівники', self)
        act_workers.setToolTip('Відкрити вікно управління працівниками')
        act_workers.triggered.connect(self._open_workers)
        toolbar.addAction(act_workers)

        toolbar.addSeparator()

        act_schedule = QAction('Побудувати розклад', self)
        act_schedule.setToolTip('Побудувати розклад за допомогою OR-Tools')
        act_schedule.triggered.connect(self._build_schedule)
        toolbar.addAction(act_schedule)

        toolbar.addSeparator()

        act_save_graph = QAction('Зберегти граф', self)
        act_save_graph.triggered.connect(self._save_graph)
        toolbar.addAction(act_save_graph)

        act_load_graph = QAction('Завантажити граф', self)
        act_load_graph.triggered.connect(self._load_graph)
        toolbar.addAction(act_load_graph)

    def _create_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu('Файл')

        act_save = QAction('Зберегти граф...', self)
        act_save.setShortcut('Ctrl+S')
        act_save.triggered.connect(self._save_graph)
        file_menu.addAction(act_save)

        act_load = QAction('Завантажити граф...', self)
        act_load.setShortcut('Ctrl+O')
        act_load.triggered.connect(self._load_graph)
        file_menu.addAction(act_load)

        file_menu.addSeparator()

        act_export = QAction('Експорт розкладу...', self)
        act_export.triggered.connect(self._export_schedule)
        file_menu.addAction(act_export)

        file_menu.addSeparator()

        act_quit = QAction('Вихід', self)
        act_quit.setShortcut('Ctrl+Q')
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        edit_menu = menubar.addMenu('Редагування')

        act_add = QAction('Додати операцію', self)
        act_add.setShortcut('Ctrl+N')
        act_add.triggered.connect(self._add_operation_node)
        edit_menu.addAction(act_add)

        act_del = QAction('Видалити обране', self)
        act_del.setShortcut('Delete')
        act_del.triggered.connect(self._delete_selected)
        edit_menu.addAction(act_del)

        tools_menu = menubar.addMenu('Інструменти')

        act_workers = QAction('Працівники...', self)
        act_workers.triggered.connect(self._open_workers)
        tools_menu.addAction(act_workers)

        act_schedule = QAction('Побудувати розклад', self)
        act_schedule.setShortcut('Ctrl+R')
        act_schedule.triggered.connect(self._build_schedule)
        tools_menu.addAction(act_schedule)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _add_operation_node(self):
        node = self._graph.create_node('schedule.nodes.OperationNode')
        node.set_pos(*self._graph.cursor_pos())
        self._log_msg(f'Додано операцію: {node.get_property("op_name")}')

    def _delete_selected(self):
        nodes = self._graph.selected_nodes()
        if nodes:
            self._graph.delete_nodes(nodes)
            self._log_msg(f'Видалено {len(nodes)} вузлів')

    def _open_workers(self):
        ops = self._get_operation_names()
        self._workers_window.set_available_operations(ops)
        self._workers_window.show()
        self._workers_window.raise_()

    def _get_operation_names(self):
        names = []
        for node in self._graph.all_nodes():
            if isinstance(node, OperationNode):
                name = node.get_property('op_name')
                if name:
                    names.append(name)
        return names

    def _extract_graph_data(self):
        operations = []
        dependencies = []

        for node in self._graph.all_nodes():
            if not isinstance(node, OperationNode):
                continue
            try:
                dur = int(node.get_property('duration'))
            except (ValueError, TypeError):
                dur = 1
            try:
                wn = int(node.get_property('workers_needed'))
            except (ValueError, TypeError):
                wn = 1
            operations.append({
                'id': node.id,
                'name': node.get_property('op_name') or 'Без назви',
                'duration': max(dur, 1),
                'workers_needed': max(wn, 1),
            })

        for node in self._graph.all_nodes():
            if not isinstance(node, OperationNode):
                continue
            for out_port in node.output_ports():
                for connected_port in out_port.connected_ports():
                    target_node = connected_port.node()
                    if isinstance(target_node, OperationNode):
                        dependencies.append((node.id, target_node.id))

        return operations, dependencies

    def _build_schedule(self):
        try:
            self._do_build_schedule()
        except Exception:
            msg = traceback.format_exc()
            self._log_msg(f'ПОМИЛКА:\n{msg}')
            QMessageBox.critical(self, 'Помилка побудови розкладу', msg)

    def _do_build_schedule(self):
        operations, dependencies = self._extract_graph_data()

        if not operations:
            QMessageBox.warning(self, 'Увага', 'Граф порожній. Додайте операції.')
            return

        workers = self._workers_window.get_workers_data()
        if not workers:
            QMessageBox.warning(self, 'Увага',
                                'Немає працівників. Відкрийте вікно працівників та додайте їх.')
            return

        self._log_msg('=' * 50)
        self._log_msg('Побудова розкладу...')
        self._log_msg(f'  Операцій: {len(operations)}, '
                      f'Залежностей: {len(dependencies)}, '
                      f'Працівників: {len(workers)}')

        result = build_schedule(operations, dependencies, workers)

        if result is None:
            QMessageBox.critical(self, 'Помилка',
                                 'Неможливо побудувати розклад.\n\n'
                                 'Перевірте:\n'
                                 '- Чи достатньо кваліфікованих працівників '
                                 'для кожної операції\n'
                                 '- Чи немає циклічних залежностей')
            self._log_msg('ПОМИЛКА: неможливо побудувати розклад')
            return

        # Виводимо результат текстово
        self._log_msg(f'\nРозклад побудовано! Загальний час: {result["makespan"]} хв\n')

        header = f'{"Операція":<25} {"Початок":>8} {"Кінець":>8} {"Трив.":>6}   Працівники'
        self._log_msg(header)
        self._log_msg('-' * len(header))

        for a in result['assignments']:
            workers_str = ', '.join(a['workers']) if a['workers'] else '—'
            self._log_msg(
                f'{a["operation_name"]:<25} {a["start"]:>8} {a["end"]:>8} '
                f'{a["duration"]:>6}   {workers_str}'
            )

        self._log_msg('=' * 50)
        self._last_schedule = result

    # ------------------------------------------------------------------
    # Save / Load
    # ------------------------------------------------------------------

    def _save_graph(self):
        path, _ = QFileDialog.getSaveFileName(
            self, 'Зберегти граф', '', 'JSON файли (*.json)')
        if not path:
            return
        if not path.endswith('.json'):
            path += '.json'

        data = {
            'graph': self._graph.serialize_session(),
            'workers': self._workers_window.get_workers_data(),
        }
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self._log_msg(f'Граф збережено: {path}')
        except Exception as e:
            QMessageBox.critical(self, 'Помилка збереження', str(e))

    def _load_graph(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Завантажити граф', '', 'JSON файли (*.json)')
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if 'graph' in data:
                self._graph.deserialize_session(data['graph'])
            if 'workers' in data:
                self._workers_window.set_workers_data(data['workers'])

            self._log_msg(f'Граф завантажено: {path}')
        except Exception as e:
            QMessageBox.critical(self, 'Помилка завантаження', str(e))

    def _export_schedule(self):
        if self._last_schedule is None:
            QMessageBox.warning(self, 'Увага', 'Спочатку побудуйте розклад.')
            return

        path, _ = QFileDialog.getSaveFileName(
            self, 'Експорт розкладу', '', 'JSON файли (*.json)')
        if not path:
            return
        if not path.endswith('.json'):
            path += '.json'

        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self._last_schedule, f, ensure_ascii=False, indent=2)
            self._log_msg(f'Розклад експортовано: {path}')
        except Exception as e:
            QMessageBox.critical(self, 'Помилка', str(e))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _log_msg(self, msg):
        self._log.append(msg)


def _global_exception_handler(exc_type, exc_value, exc_tb):
    msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(msg, file=sys.stderr)
    try:
        QMessageBox.critical(None, 'Необроблена помилка', msg)
    except Exception:
        pass


def main():
    sys.excepthook = _global_exception_handler

    app = QApplication(sys.argv)
    app.setApplicationName('ScheduleTransformer')
    app.setStyle('Fusion')

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
