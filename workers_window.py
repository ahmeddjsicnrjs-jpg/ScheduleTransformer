import json
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
    QMessageBox, QLabel, QWidget, QScrollArea,
    QLineEdit, QCompleter, QListWidget, QListWidgetItem,
    QColorDialog, QSizePolicy,
)
from PyQt5.QtCore import Qt, QStringListModel, QSortFilterProxyModel
from PyQt5.QtGui import QColor


# Default palette for new workers (cycles through)
_DEFAULT_COLORS = [
    '#4CAF50', '#2196F3', '#FF9800', '#9C27B0',
    '#F44336', '#00BCD4', '#FFEB3B', '#795548',
    '#607D8B', '#E91E63', '#3F51B5', '#8BC34A',
]


class OperationListWidget(QWidget):
    """
    Widget with a searchable dropdown to add operations
    and a list showing currently assigned operations.
    """

    def __init__(self, available_operations, selected_operations=None, parent=None):
        super().__init__(parent)
        self._available = list(available_operations)
        self._selected = list(selected_operations or [])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(2)

        # --- Search + Add row ---
        add_row = QHBoxLayout()
        add_row.setSpacing(2)

        self._search = QLineEdit()
        self._search.setPlaceholderText('Пошук операції...')
        completer = QCompleter(self._available)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self._search.setCompleter(completer)
        add_row.addWidget(self._search)

        btn_add = QPushButton('+')
        btn_add.setFixedWidth(30)
        btn_add.setToolTip('Додати операцію')
        btn_add.clicked.connect(self._add_operation)
        add_row.addWidget(btn_add)

        layout.addLayout(add_row)

        # --- List of selected operations ---
        self._list_widget = QListWidget()
        self._list_widget.setStyleSheet('QListWidget { font-size: 11px; }')
        layout.addWidget(self._list_widget)

        self._search.returnPressed.connect(self._add_operation)
        self._rebuild_list()

    def _add_operation(self):
        text = self._search.text().strip()
        if not text:
            return
        if text not in self._available:
            # Try case-insensitive match
            for op in self._available:
                if op.lower() == text.lower():
                    text = op
                    break
            else:
                return
        if text not in self._selected:
            self._selected.append(text)
            self._rebuild_list()
        self._search.clear()

    def _remove_operation(self, op_name):
        if op_name in self._selected:
            self._selected.remove(op_name)
            self._rebuild_list()

    def _rebuild_list(self):
        self._list_widget.clear()
        for op in self._selected:
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(2, 1, 2, 1)
            item_layout.setSpacing(4)

            lbl = QLabel(op)
            lbl.setStyleSheet('font-size: 11px;')
            item_layout.addWidget(lbl, 1)

            btn_del = QPushButton('\u00d7')
            btn_del.setFixedSize(20, 20)
            btn_del.setStyleSheet(
                'QPushButton { color: red; font-weight: bold; border: none; font-size: 13px; }'
                'QPushButton:hover { background: #ffcccc; border-radius: 3px; }'
            )
            btn_del.setToolTip(f'Видалити {op}')
            btn_del.clicked.connect(lambda checked, name=op: self._remove_operation(name))
            item_layout.addWidget(btn_del)

            list_item = QListWidgetItem()
            list_item.setSizeHint(item_widget.sizeHint())
            self._list_widget.addItem(list_item)
            self._list_widget.setItemWidget(list_item, item_widget)

    def get_selected_operations(self):
        return list(self._selected)


class ColorButton(QPushButton):
    """A button that shows its color and opens a color picker on click."""

    def __init__(self, color='#4CAF50', parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self.setFixedSize(36, 36)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip('Обрати колір')
        self.clicked.connect(self._pick_color)
        self._update_style()

    def _pick_color(self):
        color = QColorDialog.getColor(self._color, self, 'Обрати колір працівника')
        if color.isValid():
            self._color = color
            self._update_style()

    def _update_style(self):
        self.setStyleSheet(
            f'QPushButton {{ background-color: {self._color.name()}; '
            f'border: 2px solid {self._color.darker(130).name()}; '
            f'border-radius: 4px; }}'
            f'QPushButton:hover {{ border: 2px solid #333; }}'
        )

    def get_color(self):
        return self._color.name()

    def set_color(self, color_str):
        self._color = QColor(color_str)
        self._update_style()


class WorkersWindow(QDialog):
    """
    Вікно управління працівниками.
    Дозволяє додавати/видаляти працівників та призначати їм операції.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Управління працівниками')
        self.setMinimumSize(750, 500)

        self._workers = []  # [{'name': str, 'operations': [str, ...], 'color': str}]
        self._available_operations = []

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # --- Таблиця працівників ---
        lbl = QLabel('Працівники:')
        lbl.setStyleSheet('font-weight: bold; font-size: 14px;')
        layout.addWidget(lbl)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Ім'я працівника", 'Колір', 'Доступні операції'])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self._table.horizontalHeader().resizeSection(1, 50)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
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
        idx = len(self._workers)
        color = _DEFAULT_COLORS[idx % len(_DEFAULT_COLORS)]
        self._workers.append({
            'name': f'Працівник {idx + 1}',
            'operations': list(self._available_operations),
            'color': color,
        })
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

            # Color
            color_widget = self._table.cellWidget(row, 1)
            color = '#4CAF50'
            if color_widget:
                btn = color_widget.findChild(ColorButton)
                if btn:
                    color = btn.get_color()

            # Operations
            ops_widget = self._table.cellWidget(row, 2)
            selected_ops = []
            if ops_widget:
                op_list = ops_widget.findChild(OperationListWidget)
                if op_list:
                    selected_ops = op_list.get_selected_operations()

            workers.append({'name': name, 'operations': selected_ops, 'color': color})
        self._workers = workers

    def _refresh_table(self):
        self._table.setRowCount(len(self._workers))
        for row, worker in enumerate(self._workers):
            # Ім'я
            name_item = QTableWidgetItem(worker.get('name', ''))
            self._table.setItem(row, 0, name_item)

            # Колір
            color_container = QWidget()
            color_layout = QHBoxLayout(color_container)
            color_layout.setContentsMargins(4, 4, 4, 4)
            color_layout.setAlignment(Qt.AlignCenter)
            color_str = worker.get('color', _DEFAULT_COLORS[row % len(_DEFAULT_COLORS)])
            color_btn = ColorButton(color_str)
            color_layout.addWidget(color_btn)
            self._table.setCellWidget(row, 1, color_container)

            # Операції — випадаючий список з пошуком
            worker_ops = worker.get('operations', [])
            ops_widget = OperationListWidget(
                self._available_operations, worker_ops
            )
            self._table.setCellWidget(row, 2, ops_widget)

            self._table.setRowHeight(row, max(140, 32 * (len(worker_ops) + 2)))

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
