"""
Віджет діаграми Ганта для відображення результатів планування.
"""

from PyQt5.QtWidgets import QWidget, QScrollArea, QVBoxLayout, QLabel
from PyQt5.QtGui import QPainter, QColor, QFont, QPen, QFontMetrics
from PyQt5.QtCore import Qt, QRectF


# Палітра кольорів для операцій
_COLORS = [
    QColor(76, 175, 80),
    QColor(33, 150, 243),
    QColor(255, 152, 0),
    QColor(156, 39, 176),
    QColor(244, 67, 54),
    QColor(0, 188, 212),
    QColor(255, 235, 59),
    QColor(121, 85, 72),
    QColor(96, 125, 139),
    QColor(233, 30, 99),
    QColor(63, 81, 181),
    QColor(139, 195, 74),
]


class GanttCanvas(QWidget):
    """Полотно для малювання діаграми Ганта."""

    ROW_HEIGHT = 36
    HEADER_HEIGHT = 40
    LEFT_MARGIN = 160
    RIGHT_MARGIN = 30
    TOP_MARGIN = 10

    def __init__(self, parent=None):
        super().__init__(parent)
        self._schedule = None
        self._makespan = 0
        self.setMinimumHeight(200)

    def set_schedule(self, schedule: dict):
        self._schedule = schedule
        self._makespan = schedule.get('makespan', 0)

        # Обчислити потрібну висоту
        workers = set()
        for a in schedule.get('assignments', []):
            for w in a.get('workers', []):
                workers.add(w)
        row_count = max(len(workers), 1)
        height = self.TOP_MARGIN + self.HEADER_HEIGHT + row_count * self.ROW_HEIGHT + 40
        self.setMinimumHeight(int(height))
        self.update()

    def paintEvent(self, event):
        if not self._schedule or not self._schedule.get('assignments'):
            painter = QPainter(self)
            painter.setPen(QColor(180, 180, 180))
            painter.setFont(QFont('Arial', 12))
            painter.drawText(self.rect(), Qt.AlignCenter, 'Немає даних для відображення')
            painter.end()
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        assignments = self._schedule['assignments']
        makespan = max(self._makespan, 1)

        # Збираємо унікальних працівників у порядку появи
        worker_order = []
        seen = set()
        for a in assignments:
            for w in a.get('workers', []):
                if w not in seen:
                    worker_order.append(w)
                    seen.add(w)

        if not worker_order:
            painter.end()
            return

        # Кольори операцій
        op_names = list(dict.fromkeys(a['operation_name'] for a in assignments))
        op_color_map = {}
        for i, name in enumerate(op_names):
            op_color_map[name] = _COLORS[i % len(_COLORS)]

        width = self.width()
        chart_width = width - self.LEFT_MARGIN - self.RIGHT_MARGIN
        px_per_unit = chart_width / makespan if makespan > 0 else 1

        y0 = self.TOP_MARGIN + self.HEADER_HEIGHT

        # --- Часова шкала ---
        painter.setPen(QPen(QColor(100, 100, 100)))
        painter.setFont(QFont('Arial', 9))

        step = max(1, makespan // 20)
        for t in range(0, makespan + 1, step):
            x = self.LEFT_MARGIN + t * px_per_unit
            painter.drawLine(int(x), y0 - 5, int(x), y0 + len(worker_order) * self.ROW_HEIGHT)
            painter.drawText(int(x) - 10, y0 - 8, str(t))

        # --- Рядки працівників ---
        painter.setFont(QFont('Arial', 10))
        for row, worker_name in enumerate(worker_order):
            y = y0 + row * self.ROW_HEIGHT

            # Горизонтальна лінія-розділювач
            painter.setPen(QPen(QColor(220, 220, 220)))
            painter.drawLine(self.LEFT_MARGIN, int(y + self.ROW_HEIGHT),
                             int(width - self.RIGHT_MARGIN), int(y + self.ROW_HEIGHT))

            # Ім'я працівника
            painter.setPen(QColor(50, 50, 50))
            painter.drawText(5, int(y + 4), self.LEFT_MARGIN - 10, self.ROW_HEIGHT,
                             Qt.AlignVCenter | Qt.AlignRight, worker_name)

            # Блоки операцій
            for a in assignments:
                if worker_name not in a.get('workers', []):
                    continue

                x_start = self.LEFT_MARGIN + a['start'] * px_per_unit
                x_end = self.LEFT_MARGIN + a['end'] * px_per_unit
                bar_w = max(x_end - x_start, 2)

                color = op_color_map.get(a['operation_name'], QColor(100, 100, 100))
                painter.setBrush(color)
                painter.setPen(QPen(color.darker(130), 1))

                rect = QRectF(x_start, y + 4, bar_w, self.ROW_HEIGHT - 8)
                painter.drawRoundedRect(rect, 3, 3)

                # Текст операції
                painter.setPen(QColor(255, 255, 255))
                painter.setFont(QFont('Arial', 8, QFont.Bold))
                fm = QFontMetrics(painter.font())
                label = a['operation_name']
                avail_w = max(int(bar_w - 6), 0)
                if fm.horizontalAdvance(label) > avail_w:
                    label = fm.elidedText(label, Qt.ElideRight, avail_w)
                painter.drawText(rect.adjusted(3, 0, -3, 0),
                                 Qt.AlignVCenter | Qt.AlignLeft, label)
                painter.setFont(QFont('Arial', 10))

        painter.end()


class GanttWidget(QWidget):
    """Обгортка з прокруткою для діаграми Ганта."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._label = QLabel('Діаграма Ганта')
        self._label.setStyleSheet('font-weight: bold; font-size: 13px; padding: 4px;')
        layout.addWidget(self._label)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._canvas = GanttCanvas()
        self._scroll.setWidget(self._canvas)
        layout.addWidget(self._scroll)

    def set_schedule(self, schedule: dict):
        ms = schedule.get('makespan', 0)
        self._label.setText(f'Діаграма Ганта  —  Загальний час: {ms} хв')
        self._canvas.set_schedule(schedule)
