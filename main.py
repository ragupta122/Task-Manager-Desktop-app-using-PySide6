import sys
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QComboBox, QPushButton, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QStatusBar, QCheckBox,
)
from PySide6.QtCore import Qt

PRIORITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}


class Task:
    _next_id = 1

    def __init__(self, title, priority="Medium"):
        self.id = Task._next_id
        Task._next_id += 1
        self.title = title
        self.priority = priority
        self.done = False
        self.created = datetime.now()

    def toggle(self):
        self.done = not self.done


class TaskManagerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tasks")
        self.resize(600, 460)

        self.tasks: list[Task] = []
        self.filter_mode = "all"
        self.sort_mode = "created"
        self.sort_reverse = False

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self._build_input_row(layout)
        self._build_filter_row(layout)
        self._build_sort_row(layout)
        self._build_table(layout)
        self._build_status_bar()

        self._seed_demo_data()
        self.refresh()

    # ---------- construction ----------

    def _build_input_row(self, parent_layout):
        row = QHBoxLayout()

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Task title")
        self.title_input.returnPressed.connect(self.add_task)
        row.addWidget(self.title_input, stretch=1)

        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["High", "Medium", "Low"])
        self.priority_combo.setCurrentText("Medium")
        row.addWidget(self.priority_combo)

        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self.add_task)
        row.addWidget(add_btn)

        parent_layout.addLayout(row)

    def _build_filter_row(self, parent_layout):
        row = QHBoxLayout()
        row.addWidget(QLabel("Filter:"))

        self.filter_buttons = {}
        for mode, label in [("all", "All"), ("active", "Active"), ("done", "Done")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, m=mode: self.set_filter(m))
            row.addWidget(btn)
            self.filter_buttons[mode] = btn

        row.addStretch()
        parent_layout.addLayout(row)

    def _build_sort_row(self, parent_layout):
        row = QHBoxLayout()
        row.addWidget(QLabel("Sort by:"))

        self.sort_buttons = {}
        for mode, label in [("created", "Date"), ("priority", "Priority"), ("title", "Title")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, m=mode: self.set_sort(m))
            row.addWidget(btn)
            self.sort_buttons[mode] = btn

        row.addStretch()
        parent_layout.addLayout(row)

    def _build_table(self, parent_layout):
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Done", "Task", "Priority", "Status"])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 44)
        header.setSectionResizeMode(1, QHeaderView.Stretch)

        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self.on_row_double_click)

        parent_layout.addWidget(self.table)

    def _build_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def _seed_demo_data(self):
        self.tasks.append(Task("Write unit tests", "High"))
        self.tasks.append(Task("Refactor auth module", "Medium"))
        self.tasks.append(Task("Update README", "Low"))
        self.tasks[2].done = True

    # ---------- actions ----------

    def add_task(self):
        title = self.title_input.text().strip()
        if not title:
            QMessageBox.warning(self, "Missing title", "Enter a task title first.")
            return

        task = Task(title, self.priority_combo.currentText())
        self.tasks.append(task)
        self.title_input.clear()
        self.refresh()

    def set_filter(self, mode):
        self.filter_mode = mode
        self.refresh()

    def set_sort(self, mode):
        if self.sort_mode == mode:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_mode = mode
            self.sort_reverse = False
        self.refresh()

    def set_done(self, task, state):
        task.done = (state == Qt.Checked.value)
        self.refresh()

    def on_row_double_click(self, row, column):
        task = self._task_at_row(row)
        if task:
            task.toggle()
            self.refresh()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Backspace, Qt.Key_Delete):
            self.delete_selected()
        else:
            super().keyPressEvent(event)

    def delete_selected(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        task = self._task_at_row(rows[0].row())
        if task:
            self.tasks.remove(task)
            self.refresh()

    def _task_at_row(self, row):
        task_id = self.table.item(row, 1).data(Qt.UserRole)
        return next((t for t in self.tasks if t.id == task_id), None)

    # ---------- rendering ----------

    def visible_tasks(self):
        if self.filter_mode == "active":
            tasks = [t for t in self.tasks if not t.done]
        elif self.filter_mode == "done":
            tasks = [t for t in self.tasks if t.done]
        else:
            tasks = list(self.tasks)

        if self.sort_mode == "priority":
            key = lambda t: PRIORITY_ORDER[t.priority]
        elif self.sort_mode == "title":
            key = lambda t: t.title.lower()
        else:
            key = lambda t: t.created

        tasks.sort(key=key, reverse=self.sort_reverse)
        return tasks

    def refresh(self):
        visible = self.visible_tasks()
        self.table.setRowCount(len(visible))

        for row, task in enumerate(visible):
            checkbox = QCheckBox()
            checkbox.setChecked(task.done)
            checkbox.stateChanged.connect(lambda state, t=task: self.set_done(t, state))

            cell_wrapper = QWidget()
            cell_layout = QHBoxLayout(cell_wrapper)
            cell_layout.addWidget(checkbox)
            cell_layout.setAlignment(Qt.AlignCenter)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(row, 0, cell_wrapper)

            title_item = QTableWidgetItem(task.title)
            title_item.setData(Qt.UserRole, task.id)
            priority_item = QTableWidgetItem(task.priority)
            status_item = QTableWidgetItem("Done" if task.done else "Active")

            if task.done:
                for item in (title_item, priority_item, status_item):
                    item.setForeground(Qt.gray)

            self.table.setItem(row, 1, title_item)
            self.table.setItem(row, 2, priority_item)
            self.table.setItem(row, 3, status_item)

        for mode, btn in self.filter_buttons.items():
            btn.setChecked(mode == self.filter_mode)
        for mode, btn in self.sort_buttons.items():
            btn.setChecked(mode == self.sort_mode)

        active_count = sum(1 for t in self.tasks if not t.done)
        arrow = " ↓" if self.sort_reverse else " ↑"
        self.status_bar.showMessage(
            f"{len(visible)} shown · {active_count} active · sorted by {self.sort_mode}{arrow}"
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TaskManagerWindow()
    window.show()
    sys.exit(app.exec())