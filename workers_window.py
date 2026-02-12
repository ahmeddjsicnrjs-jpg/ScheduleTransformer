import json
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
    QMessageBox, QLabel, QWidget,
    QLineEdit, QListWidget, QListWidgetItem,
    QColorDialog,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor


# Default palette for new workers (cycles through)
_DEFAULT_COLORS = [
    '#4CAF50', '#2196F3', '#FF9800', '#9C27B0',
    '#F44336', '#00BCD4', '#FFEB3B', '#795548',
    '#607D8B', '#E91E63', '#3F51B5', '#8BC34A',
]


class OperationListWidget(QWidget):
    """
    Widget with two lists: available operations (with search filter)
    and selected operations. Click to add/remove.
    """

    def __init__(self, available_operations, selected_operations=None, parent=None):
        super().__init__(parent)
        self._available = list(available_operations)
        self._selected = list(selected_operations or [])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(2)

        # --- Search field ---
        self._search = QLineEdit()
        self._search.setPlaceholderText('Пошук операції...')
        self._search.textChanged.connect(self._filter_available)
        layout.addWidget(self._search)

        # --- Available operations list ---
        lbl_avail = QLabel('Доступні:')
        lbl_avail.setStyleSheet('font-size: 10px; color: #666; margin-top: 2px;')
        layout.addWidget(lbl_avail)

        self._available_list = QListWidget()
        self._available_list.setStyleSheet(
            'QListWidget { font-size: 11px; }'
            'QListWidget::item { padding: 2px 4px; }'
            'QListWidget::item:hover { background: #e8f5e9; }'
        )
        self._available_list.itemDoubleClicked.connect(self._on_available_clicked)
        layout.addWidget(self._available_list, 1)

        # --- Selected operations list ---
        lbl_sel = QLabel('Обрані:')
        lbl_sel.setStyleSheet('font-size: 10px; color: #666; margin-top: 2px;')
        layout.addWidget(lbl_sel)

        self._selected_list = QListWidget()
        self._selected_list.setStyleSheet(
            'QListWidget { font-size: 11px; }'
            'QListWidget::item { padding: 2px 4px; }'
            'QListWidget::item:hover { background: #ffebee; }'
        )
        self._selected_list.itemDoubleClicked.connect(self._on_selected_clicked)
        layout.addWidget(self._selected_list, 1)

        self._rebuild_lists()

    def _filter_available(self, text):
        """Filter available operations list by search text."""
        text = text.strip().lower()
        for i in range(self._available_list.count()):
            item = self._available_list.item(i)
            if text:
                item.setHidden(text not in item.text().lower())
            else:
                item.setHidden(False)

    def _on_available_clicked(self, item):
        op = item.text().lstrip('+ ')
        if op in self._available and op not in self._selected:
            self._selected.append(op)
            self._rebuild_lists()

    def _on_selected_clicked(self, item):
        op = item.text().lstrip('\u00d7 ')
        if op in self._selected:
            self._selected.remove(op)
            self._rebuild_lists()

    def _rebuild_lists(self):
        # Available (not yet selected)
        self._available_list.clear()
        not_selected = [op for op in self._available if op not in self._selected]
        for op in not_selected:
            item = QListWidgetItem(f'+ {op}')
            item.setForeground(QColor(56, 142, 60))
            self._available_list.addItem(item)

        if not not_selected and not self._available:
            item = QListWidgetItem('(немає операцій у графі)')
            item.setForeground(QColor(160, 160, 160))
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            self._available_list.addItem(item)
        elif not not_selected:
            item = QListWidgetItem('(всі операції обрані)')
            item.setForeground(QColor(160, 160, 160))
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            self._available_list.addItem(item)

        # Selected
        self._selected_list.clear()
        for op in self._selected:
            item = QListWidgetItem(f'\u00d7 {op}')
            item.setForeground(QColor(198, 40, 40))
            self._selected_list.addItem(item)

        # Re-apply search filter
        self._filter_available(self._search.text())

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
            if isinstance(ops_widget, OperationListWidget):
                selected_ops = ops_widget.get_selected_operations()

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

            total_ops = len(self._available_operations) + len(worker_ops)
            self._table.setRowHeight(row, max(180, 22 * total_ops + 80))

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
