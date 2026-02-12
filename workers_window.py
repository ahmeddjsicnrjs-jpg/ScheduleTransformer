import json
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
    QMessageBox, QLabel, QCheckBox, QWidget, QScrollArea,
    QGroupBox, QLineEdit,
)
from PyQt5.QtCore import Qt


class WorkersWindow(QDialog):
    """
    Вікно управління працівниками.
    Дозволяє додавати/видаляти працівників та призначати їм операції.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Управління працівниками')
        self.setMinimumSize(700, 500)

        self._workers = []  # [{'name': str, 'operations': [str, ...]}]
        self._available_operations = []

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # --- Таблиця працівників ---
        lbl = QLabel('Працівники:')
        lbl.setStyleSheet('font-weight: bold; font-size: 14px;')
        layout.addWidget(lbl)

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["Ім'я працівника", 'Доступні операції'])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self._table)

        # --- Кнопки додавання / видалення ---
        btn_row = QHBoxLayout()

        btn_add = QPushButton('+ Додати працівника')
        btn_add.clicked.connect(self._add_worker)
        btn_row.addWidget(btn_add)

        btn_remove = QPushButton('- Видалити обраного')
        btn_remove.clicked.connect(self._remove_worker)
        btn_row.addWidget(btn_remove)

        layout.addLayout(btn_row)

        # --- Зберегти / Завантажити ---
        file_row = QHBoxLayout()

        btn_save = QPushButton('Зберегти у файл')
        btn_save.clicked.connect(self.save_to_file)
        file_row.addWidget(btn_save)

        btn_load = QPushButton('Завантажити з файлу')
        btn_load.clicked.connect(self.load_from_file)
        file_row.addWidget(btn_load)

        layout.addLayout(file_row)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_available_operations(self, operations: list[str]):
        """Оновити список доступних операцій (з графа)."""
        self._available_operations = sorted(set(operations))
        self._refresh_table()

    def get_workers_data(self) -> list[dict]:
        """Повернути дані працівників у форматі списку словників."""
        self._sync_from_table()
        return self._workers

    def set_workers_data(self, workers: list[dict]):
        self._workers = workers
        self._refresh_table()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _add_worker(self):
        self._sync_from_table()
        self._workers.append({'name': f'Працівник {len(self._workers) + 1}',
                              'operations': list(self._available_operations)})
        self._refresh_table()

    def _remove_worker(self):
        rows = sorted(set(idx.row() for idx in self._table.selectedIndexes()),
                      reverse=True)
        if not rows:
            return
        self._sync_from_table()
        for r in rows:
            if r < len(self._workers):
                self._workers.pop(r)
        self._refresh_table()

    def _sync_from_table(self):
        """Зчитати стан таблиці назад у self._workers."""
        workers = []
        for row in range(self._table.rowCount()):
            name_item = self._table.item(row, 0)
            name = name_item.text() if name_item else f'Працівник {row + 1}'

            ops_widget = self._table.cellWidget(row, 1)
            selected_ops = []
            if ops_widget:
                scroll = ops_widget.findChild(QScrollArea)
                if scroll:
                    container = scroll.widget()
                    if container:
                        for cb in container.findChildren(QCheckBox):
                            if cb.isChecked():
                                selected_ops.append(cb.text())
            workers.append({'name': name, 'operations': selected_ops})
        self._workers = workers

    def _refresh_table(self):
        self._table.setRowCount(len(self._workers))
        for row, worker in enumerate(self._workers):
            # Ім'я
            name_item = QTableWidgetItem(worker.get('name', ''))
            self._table.setItem(row, 0, name_item)

            # Чекбокси операцій
            container_widget = QWidget()
            container_layout = QVBoxLayout(container_widget)
            container_layout.setContentsMargins(4, 2, 4, 2)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            inner = QWidget()
            inner_layout = QVBoxLayout(inner)
            inner_layout.setContentsMargins(2, 2, 2, 2)

            worker_ops = worker.get('operations', [])
            for op in self._available_operations:
                cb = QCheckBox(op)
                cb.setChecked(op in worker_ops)
                inner_layout.addWidget(cb)

            if not self._available_operations:
                lbl = QLabel('(немає операцій у графі)')
                lbl.setStyleSheet('color: gray;')
                inner_layout.addWidget(lbl)

            inner_layout.addStretch()
            scroll.setWidget(inner)
            container_layout.addWidget(scroll)

            self._table.setCellWidget(row, 1, container_widget)
            self._table.setRowHeight(row, max(120, 30 * len(self._available_operations)))

    # ------------------------------------------------------------------
    # File I/O
    # ------------------------------------------------------------------

    def save_to_file(self):
        self._sync_from_table()
        path, _ = QFileDialog.getSaveFileName(
            self, 'Зберегти працівників', '', 'JSON файли (*.json)')
        if not path:
            return
        if not path.endswith('.json'):
            path += '.json'
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self._workers, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, 'Збережено',
                                   f'Працівників збережено у {path}')
        except Exception as e:
            QMessageBox.critical(self, 'Помилка', str(e))

    def load_from_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Завантажити працівників', '', 'JSON файли (*.json)')
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise ValueError('Невірний формат файлу')
            self._workers = data
            self._refresh_table()
            QMessageBox.information(self, 'Завантажено',
                                   f'Працівників завантажено з {path}')
        except Exception as e:
            QMessageBox.critical(self, 'Помилка', str(e))
