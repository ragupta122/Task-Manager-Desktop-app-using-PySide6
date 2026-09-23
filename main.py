import sys                                             # built-in module: lets us exit the program with a proper exit code at the end
from datetime import datetime                          # built-in: gives us a way to record "when was this task created"
from PySide6.QtWidgets import (                         # PySide6's visible-widget toolkit — everything you can see and click
    QApplication,                                       # represents the running GUI application itself; every app needs exactly one
    QMainWindow,                                         # a ready-made window with title bar, resizing, status bar support, etc.
    QWidget,                                             # a plain, blank container — the base building block for grouping things
    QVBoxLayout,                                         # arranges child widgets in a vertical stack, top to bottom
    QHBoxLayout,                                         # arranges child widgets in a horizontal row, left to right
    QLineEdit,                                           # a single-line text input box
    QComboBox,                                           # a dropdown selection menu
    QPushButton,                                         # a clickable button
    QLabel,                                              # non-editable text, used here as headings
    QTableWidget,                                        # a spreadsheet-like grid of rows and columns
    QTableWidgetItem,                                    # one plain-text cell inside a QTableWidget
    QHeaderView,                                         # controls how a table's column headers behave (fixed width, stretch, etc.)
    QMessageBox,                                         # pop-up dialog boxes (used here for the "missing title" warning)
    QStatusBar,                                          # the thin status strip along the bottom of the window
    QCheckBox,                                           # a tickable checkbox widget
)
from PySide6.QtCore import Qt                           # a bag of named constants (Qt.Checked, Qt.gray, Qt.Key_Delete, etc.)

PRIORITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}     # maps each priority word to a rank number, so sorting by priority means sorting by importance, not alphabetically


class Task:                                              # blueprint describing what one task looks like and can do
    _next_id = 1                                          # CLASS attribute: one shared counter, belongs to Task itself, not to any single task

    def __init__(self, title, priority="Medium"):         # runs automatically every time a new Task is created
        self.id = Task._next_id                           # give this task the current value of the shared counter as its own personal id
        Task._next_id += 1                                 # bump the SHARED counter (via Task, not self) so the next task gets a different id
        self.title = title                                 # store this task's own title (instance attribute — unique to this object)
        self.priority = priority                           # store this task's own priority
        self.done = False                                  # every new task starts as not-yet-completed
        self.created = datetime.now()                      # record the exact moment this task was created, for sorting by date later

    def toggle(self):                                       # flips this task between done and not-done
        self.done = not self.done                            # "not True" becomes False, "not False" becomes True


class TaskManagerWindow(QMainWindow):                     # our window; inherits all of QMainWindow's built-in behavior
    def __init__(self):                                    # runs once, when the window is first created
        super().__init__()                                  # run QMainWindow's own setup first, before we add anything of our own

        self.setWindowTitle("Tasks")                        # text shown in the window's title bar
        self.resize(600, 460)                               # starting window size in pixels: width, height

        self.tasks: list[Task] = []                         # THE single source of truth — every task that exists lives in this list
        self.filter_mode = "all"                            # which filter is currently active: "all" | "active" | "done"
        self.sort_mode = "created"                          # which field we're sorting by: "created" | "priority" | "title"
        self.sort_reverse = False                           # whether that sort is currently reversed (descending)

        central = QWidget()                                 # a blank container to hold everything else in the window
        self.setCentralWidget(central)                      # tell the window "this widget is the main content area"
        layout = QVBoxLayout(central)                       # a vertical layout, attached to `central`, that stacks its children top to bottom

        self._build_input_row(layout)                       # build the title/priority/Add-button row and place it in the layout
        self._build_filter_row(layout)                      # build the All/Active/Done filter buttons and place them
        self._build_sort_row(layout)                        # build the Date/Priority/Title sort buttons and place them
        self._build_table(layout)                           # build the empty task table and place it
        self._build_status_bar()                            # build the status bar at the bottom of the window

        self._seed_demo_data()                              # add a few starter tasks so the window isn't empty on first launch
        self.refresh()                                      # draw the table for the very first time, based on the seeded data

    # ---------- construction ----------

    def _build_input_row(self, parent_layout):             # builds the "type a task, pick priority, click Add" row
        row = QHBoxLayout()                                  # a horizontal layout just for this row's widgets

        self.title_input = QLineEdit()                       # the text box the user types a new task's title into
        self.title_input.setPlaceholderText("Task title")    # faint grey hint text shown while the box is empty
        self.title_input.returnPressed.connect(self.add_task)  # pressing Enter in this box calls add_task (note: no parentheses — passing the function, not calling it now)
        row.addWidget(self.title_input, stretch=1)            # add it to the row; stretch=1 makes it grow to fill extra space on resize

        self.priority_combo = QComboBox()                    # the dropdown for choosing a new task's priority
        self.priority_combo.addItems(["High", "Medium", "Low"])  # the three options available in the dropdown
        self.priority_combo.setCurrentText("Medium")          # which option is selected by default
        row.addWidget(self.priority_combo)                    # add it to the row (no stretch — stays its natural size)

        add_btn = QPushButton("Add")                          # the clickable "Add" button
        add_btn.clicked.connect(self.add_task)                # clicking it also calls add_task — same action as pressing Enter
        row.addWidget(add_btn)                                # add it to the row

        parent_layout.addLayout(row)                          # insert this whole horizontal row into the main vertical layout

    def _build_filter_row(self, parent_layout):              # builds the "Filter: All / Active / Done" row
        row = QHBoxLayout()                                    # a horizontal layout for this row
        row.addWidget(QLabel("Filter:"))                       # a plain text heading, created and added in one line since we never need it again

        self.filter_buttons = {}                               # will map each mode name ("all", "active", "done") to its actual button object

        for mode, label in [("all", "All"), ("active", "Active"), ("done", "Done")]:  # loop over three (mode, label) pairs, unpacking each tuple
            btn = QPushButton(label)                            # create a button showing this iteration's label ("All", then "Active", then "Done")
            btn.setCheckable(True)                              # lets the button stay visually pressed-in once clicked, to show which filter is active
            btn.clicked.connect(lambda checked, m=mode: self.set_filter(m))  # m=mode freezes THIS iteration's mode now, so all three buttons don't end up sharing the loop's final value
            row.addWidget(btn)                                  # add the button to the row
            self.filter_buttons[mode] = btn                     # remember this button under its mode name, so refresh() can find and update it later

        row.addStretch()                                        # invisible spacer that soaks up leftover space, keeping the buttons pushed to the left
        parent_layout.addLayout(row)                            # insert this row into the main vertical layout

    def _build_sort_row(self, parent_layout):                 # builds the "Sort by: Date / Priority / Title" row — same pattern as the filter row
        row = QHBoxLayout()                                     # a horizontal layout for this row
        row.addWidget(QLabel("Sort by:"))                       # heading label

        self.sort_buttons = {}                                  # will map each sort mode name to its button object

        for mode, label in [("created", "Date"), ("priority", "Priority"), ("title", "Title")]:  # loop over the three sort options
            btn = QPushButton(label)                             # create this iteration's button
            btn.setCheckable(True)                               # lets it show as pressed-in when active
            btn.clicked.connect(lambda checked, m=mode: self.set_sort(m))  # same frozen-default trick as the filter row, calling set_sort instead
            row.addWidget(btn)                                    # add it to the row
            self.sort_buttons[mode] = btn                        # remember it under its mode name

        row.addStretch()                                         # push the buttons to the left, same as the filter row
        parent_layout.addLayout(row)                             # insert this row into the main vertical layout

    def _build_table(self, parent_layout):                    # builds the empty task table itself
        self.table = QTableWidget(0, 4)                          # start with 0 rows (no tasks loaded yet) and 4 columns
        self.table.setHorizontalHeaderLabels(["Done", "Task", "Priority", "Status"])  # column header text, left to right

        header = self.table.horizontalHeader()                   # the object controlling column widths/behavior
        header.setSectionResizeMode(0, QHeaderView.Fixed)         # column 0 (checkbox) never resizes on its own
        self.table.setColumnWidth(0, 44)                          # ...and is fixed at exactly 44 pixels wide, just enough for a checkbox
        header.setSectionResizeMode(1, QHeaderView.Stretch)       # column 1 (task title) expands to fill any leftover width on resize

        self.table.setSelectionBehavior(QTableWidget.SelectRows)  # clicking any cell selects the whole row it's in
        self.table.setSelectionMode(QTableWidget.SingleSelection) # only one row can be selected at a time
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)   # disable the default "double-click to type into a cell" behavior

        self.table.cellDoubleClicked.connect(self.on_row_double_click)  # double-clicking any cell calls on_row_double_click(row, column)

        parent_layout.addWidget(self.table)                       # add the finished, empty table into the main layout

    def _build_status_bar(self):                              # builds the thin status strip at the bottom of the window
        self.status_bar = QStatusBar()                           # create the status bar widget
        self.setStatusBar(self.status_bar)                       # tell the window "this is your status bar"

    def _seed_demo_data(self):                                # adds a few starter tasks so the app isn't empty on first launch
        self.tasks.append(Task("Write unit tests", "High"))      # create and add task #1
        self.tasks.append(Task("Refactor auth module", "Medium"))# create and add task #2
        self.tasks.append(Task("Update README", "Low"))          # create and add task #3
        self.tasks[2].done = True                                 # mark the third task (index 2 — counting starts at 0) as already completed

    # ---------- actions ----------

    def add_task(self):                                       # runs when Add is clicked or Enter is pressed in the title box
        title = self.title_input.text().strip()                 # read the typed text, then strip leading/trailing whitespace

        if not title:                                            # an empty string is "falsy", so this catches an empty (or whitespace-only) title
            QMessageBox.warning(self, "Missing title", "Enter a task title first.")  # show a small warning dialog
            return                                                # stop here — don't create a task from an empty title

        task = Task(title, self.priority_combo.currentText())    # create a new Task using the typed title and the dropdown's current selection
        self.tasks.append(task)                                   # add it to the master list of tasks
        self.title_input.clear()                                  # empty the text box, ready for the next entry
        self.refresh()                                            # redraw the table so the new task actually appears

    def set_filter(self, mode):                              # runs when a filter button is clicked
        self.filter_mode = mode                                   # remember which filter is now active
        self.refresh()                                            # redraw to reflect the new filter

    def set_sort(self, mode):                                 # runs when a sort button is clicked
        if self.sort_mode == mode:                                # if the SAME sort field was clicked again...
            self.sort_reverse = not self.sort_reverse                 # ...flip the direction (ascending <-> descending)
        else:                                                      # otherwise, a DIFFERENT sort field was chosen...
            self.sort_mode = mode                                     # ...switch to it...
            self.sort_reverse = False                                 # ...and reset direction to ascending, rather than keeping the old field's direction
        self.refresh()                                            # redraw with the new sort settings

    def set_done(self, task, state):                         # runs when a row's checkbox is ticked or unticked
        task.done = (state == Qt.Checked.value)                  # convert the checkbox's raw state into a plain True/False and store it on the task
        self.refresh()                                           # redraw so the status column and greying-out update immediately

    def on_row_double_click(self, row, column):               # runs when any table cell is double-clicked
        task = self._task_at_row(row)                            # figure out which actual Task object this row represents
        if task:                                                  # if a real task was found (not None)...
            task.toggle()                                          # ...flip its done status...
            self.refresh()                                         # ...and redraw to show the change

    def keyPressEvent(self, event):                          # overrides QMainWindow's built-in key handler to add our own behavior
        if event.key() in (Qt.Key_Backspace, Qt.Key_Delete):      # if the key pressed was Backspace or Delete...
            self.delete_selected()                                  # ...delete whichever task row is currently selected
        else:                                                      # for every OTHER key...
            super().keyPressEvent(event)                             # ...hand it off to the normal built-in behavior, so typing/arrows/etc. still work

    def delete_selected(self):                                # deletes whichever task row is currently selected
        rows = self.table.selectionModel().selectedRows()        # get the list of currently selected row indicators
        if not rows:                                              # an empty list means nothing is selected...
            return                                                  # ...so there's nothing to delete — stop here

        task = self._task_at_row(rows[0].row())                   # get the plain row number of the (only) selected row, then find its Task
        if task:                                                   # if a real task was found...
            self.tasks.remove(task)                                  # ...remove it from the master list...
            self.refresh()                                           # ...and redraw without it

    def _task_at_row(self, row):                              # given a table row number, finds the matching Task object
        task_id = self.table.item(row, 1).data(Qt.UserRole)      # read the invisible id we stashed on the title cell (column 1) back in refresh()
        return next((t for t in self.tasks if t.id == task_id), None)  # search self.tasks for a task with a matching id; None if not found

    # ---------- rendering ----------

    def visible_tasks(self):                                  # returns the current filtered-and-sorted list of tasks to display
        if self.filter_mode == "active":                          # if the "Active" filter is on...
            tasks = [t for t in self.tasks if not t.done]            # ...keep only tasks that are NOT done
        elif self.filter_mode == "done":                           # if the "Done" filter is on...
            tasks = [t for t in self.tasks if t.done]                 # ...keep only tasks that ARE done
        else:                                                       # otherwise ("All" filter)...
            tasks = list(self.tasks)                                  # ...make a COPY of the full list (so sorting it below doesn't reorder the real data)

        if self.sort_mode == "priority":                           # if sorting by priority...
            key = lambda t: PRIORITY_ORDER[t.priority]                 # ...sort by each task's numeric priority rank, not the word itself
        elif self.sort_mode == "title":                             # if sorting by title...
            key = lambda t: t.title.lower()                            # ...sort by the lowercased title, so case doesn't affect ordering
        else:                                                        # otherwise (sorting by date)...
            key = lambda t: t.created                                   # ...sort by each task's creation timestamp

        tasks.sort(key=key, reverse=self.sort_reverse)              # actually sort the list in place, using whichever key was chosen, honoring the reverse flag
        return tasks                                                 # hand back the finished, filtered-and-sorted list

    def refresh(self):                                        # rebuilds the ENTIRE visible table from the current state — the one function that touches the screen
        visible = self.visible_tasks()                            # get the current filtered-and-sorted list to display
        self.table.setRowCount(len(visible))                      # resize the table to have exactly that many rows (old rows are wiped)

        for row, task in enumerate(visible):                      # loop through the list, getting both a row number and the task at that position

            checkbox = QCheckBox()                                  # create a fresh checkbox for this row
            checkbox.setChecked(task.done)                          # set its initial ticked state to match this task's actual done status
            checkbox.stateChanged.connect(lambda state, t=task: self.set_done(t, state))  # t=task freezes THIS row's task, same frozen-default trick as the filter/sort buttons

            cell_wrapper = QWidget()                                # a plain container, needed because a table cell can't hold a real widget directly
            cell_layout = QHBoxLayout(cell_wrapper)                 # a tiny horizontal layout attached to that container
            cell_layout.addWidget(checkbox)                         # put the checkbox inside that tiny layout
            cell_layout.setAlignment(Qt.AlignCenter)                # center the checkbox within its cell
            cell_layout.setContentsMargins(0, 0, 0, 0)              # remove all padding around it (left, top, right, bottom all zero)
            self.table.setCellWidget(row, 0, cell_wrapper)          # place the whole wrapper (checkbox and all) into column 0 of this row

            title_item = QTableWidgetItem(task.title)               # a plain text cell showing the task's title
            title_item.setData(Qt.UserRole, task.id)                # secretly attach this task's id to the cell, so _task_at_row can find it later
            priority_item = QTableWidgetItem(task.priority)          # a plain text cell showing the priority word
            status_item = QTableWidgetItem("Done" if task.done else "Active")  # "Done" if the task is complete, otherwise "Active"

            if task.done:                                            # if this task is marked complete...
                for item in (title_item, priority_item, status_item):   # ...loop over all three of its text cells...
                    item.setForeground(Qt.gray)                           # ...and turn their text grey, as a visual "completed" cue

            self.table.setItem(row, 1, title_item)                   # place the title cell into column 1
            self.table.setItem(row, 2, priority_item)                # place the priority cell into column 2
            self.table.setItem(row, 3, status_item)                  # place the status cell into column 3

        for mode, btn in self.filter_buttons.items():               # loop over every filter button, by name and object together
            btn.setChecked(mode == self.filter_mode)                   # press it in if its mode matches the currently active filter, release otherwise
        for mode, btn in self.sort_buttons.items():                  # same idea for the sort buttons
            btn.setChecked(mode == self.sort_mode)                      # press in whichever one matches the current sort mode

        active_count = sum(1 for t in self.tasks if not t.done)      # count how many tasks (across ALL tasks, not just visible ones) are still not done
        arrow = " ↓" if self.sort_reverse else " ↑"                  # pick a down-arrow if sort is reversed, otherwise an up-arrow
        self.status_bar.showMessage(                                  # build and display the status bar text
            f"{len(visible)} shown · {active_count} active · sorted by {self.sort_mode}{arrow}"  # an f-string, filling in the live current values
        )


if __name__ == "__main__":                                    # only run the code below if this file was launched directly, not imported elsewhere
    app = QApplication(sys.argv)                                  # create the one required application object, passing along any command-line arguments
    window = TaskManagerWindow()                                   # create an actual instance of our window (this is when __init__ runs and everything gets built)
    window.show()                                                   # make the window actually visible on screen
    sys.exit(app.exec())                                            # start Qt's event loop (blocks here until the window closes), then exit with its return code