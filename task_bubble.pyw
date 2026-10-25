"""Task Bubble: a pastel, always-on-top Windows task panel."""

from __future__ import annotations

import json
import os
import uuid
import ctypes
import calendar
from ctypes import wintypes
from datetime import date, datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

try:
    import winsound
except ImportError:
    winsound = None


APP_NAME = "Task Bubble"
BG = "#e9afe8"          # lavender desktop / window surround
MINT = "#f7f0dc"        # warm paper panels
PANEL = "#fffbee"
PANEL_ALT = "#f2ead6"
TEXT = "#302b33"
ACCENT = "#302b33"
MUTED = "#786e78"
RED = "#e67f78"
YELLOW = "#d5ad54"
OUTLINE = "#302b33"
UI_FONT = "Courier New"
PASTELS = ("#ffc8aa", "#ffe2a0", "#fff3a6", "#d8f3bd", "#bfeafa", "#ffcbd3")


def data_file() -> Path:
    folder = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "TaskBubble"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "tasks.json"


def acquire_single_instance() -> tuple[int | None, bool]:
    """Return a mutex handle and whether another Task Bubble instance is active."""
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = (ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p)
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
        kernel32.CloseHandle.restype = ctypes.c_bool
        handle = kernel32.CreateMutexW(None, True, "Local\\TaskBubble.Desktop.SingleInstance")
        if not handle:
            return None, False
        if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
            kernel32.CloseHandle(handle)
            return None, True
        return handle, False
    except (AttributeError, OSError):
        return None, False


class TaskBubble:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.path = data_file()
        self.tasks = self.load_tasks()
        self.sort_mode = tk.StringVar(value="Sort")
        self.view_mode = tk.StringVar(value="All")
        self.title_var = tk.StringVar()
        self.date_var = tk.StringVar()
        self.priority_var = tk.StringVar(value="Medium")
        self.color_var = tk.StringVar(value=PASTELS[0])
        self.show_done = tk.BooleanVar(value=False)
        self.drag_origin: tuple[int, int] | None = None
        self.drag_moved = False
        self.bubble_mode = False
        self.bubble_window: tk.Toplevel | None = None
        self.bubble_canvas: tk.Canvas | None = None
        self.date_picker_window: tk.Toplevel | None = None

        self.root.title(APP_NAME)
        self.root.configure(bg=BG)
        self.root.attributes("-topmost", True)
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("TaskBubble.Desktop.TaskBubble")
        except (AttributeError, OSError):
            pass
        try:
            self.root.iconbitmap(default=str(Path(__file__).with_name("task_bubble.ico")))
        except tk.TclError:
            pass
        self.root.update_idletasks()
        self.normal_geometry = self.corner_geometry(400, 660)
        self.bubble_geometry = self.corner_geometry(68, 68, margin=8)
        self.root.geometry(self.normal_geometry)
        self.root.minsize(350, 520)
        self.root.protocol("WM_DELETE_WINDOW", self.collapse)
        self.set_style()
        self.build_panel()
        self.show_list_page()

    def work_area(self) -> tuple[int, int, int, int]:
        """Return the Windows work area, excluding the taskbar."""
        try:
            rect = wintypes.RECT()
            ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)
            return rect.left, rect.top, rect.right, rect.bottom
        except (AttributeError, OSError):
            return 0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight()

    def corner_geometry(self, width: int, height: int, margin: int = 16) -> str:
        left, top, right, bottom = self.work_area()
        x = max(left + margin, right - width - margin)
        y = max(top + margin, bottom - height - margin)
        return f"{width}x{height}+{x}+{y}"

    def set_style(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TCombobox", fieldbackground=PANEL_ALT, background=PANEL_ALT,
                        foreground=TEXT, arrowcolor=TEXT, bordercolor=OUTLINE,
                        font=(UI_FONT, 9), padding=4, relief="flat")
        style.map("TCombobox", fieldbackground=[("readonly", PANEL_ALT)],
                  foreground=[("readonly", TEXT)])

    def load_tasks(self) -> list[dict]:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        except (OSError, json.JSONDecodeError):
            pass
        return []

    def save_tasks(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.tasks, ensure_ascii=False, indent=2), encoding="utf-8")

    def build_panel(self) -> None:
        self.root.overrideredirect(True)
        self.shell = tk.Frame(self.root, bg=OUTLINE, highlightthickness=2, highlightbackground=OUTLINE)
        self.shell.pack(fill="both", expand=True)
        self.page = tk.Frame(self.shell, bg=BG, highlightthickness=1, highlightbackground=OUTLINE)
        self.page.pack(fill="both", expand=True)

    def make_header(self, title: str, subtitle: str, back: bool = False) -> tk.Frame:
        header = tk.Frame(self.page, bg=BG, height=162,
                          highlightthickness=1, highlightbackground=OUTLINE)
        header.pack(fill="x")
        header.pack_propagate(False)
        self.drag_bind(header)
        top = tk.Frame(header, bg=BG)
        top.pack(fill="x", padx=15, pady=(12, 0))
        self.drag_bind(top)
        if back:
            self.text_button(top, "<", self.show_list_page, bg=BG, size=18).pack(side="left")
        count = sum(not task.get("done", False) for task in self.tasks)
        self.text_button(top, f"[{count}]", lambda: None, bg=BG, size=10).pack(side="right", padx=(4, 0))
        self.text_button(top, "−", self.collapse, bg=BG, size=15).pack(side="right", padx=(4, 0))
        self.text_button(top, "X", self.quit_app, bg=BG, size=10).pack(side="right", padx=(4, 0))
        title_label = tk.Label(header, text=title, bg=BG, fg=TEXT, anchor="w",
                               font=(UI_FONT, 16, "bold"))
        title_label.pack(fill="x", padx=20, pady=(17, 0))
        self.drag_bind(title_label)
        subtitle_label = tk.Label(header, text=subtitle, bg=BG, fg=MUTED, anchor="w",
                                  font=(UI_FONT, 8))
        subtitle_label.pack(fill="x", padx=20, pady=(0, 4))
        self.drag_bind(subtitle_label)
        return header

    def text_button(self, parent: tk.Widget, label: str, command, bg: str = PANEL,
                    size: int = 10) -> tk.Button:
        return tk.Button(parent, text=label, command=command, bg=bg, fg=TEXT,
                         activebackground=bg, activeforeground=TEXT, relief="flat", bd=0,
                         font=(UI_FONT, size, "bold"), cursor="hand2", padx=4, pady=2,
                         highlightthickness=1, highlightbackground=OUTLINE)

    def primary_button(self, parent: tk.Widget, label: str, command) -> tk.Button:
        return tk.Button(parent, text=label, command=command, bg=ACCENT, fg="white",
                         activebackground="#535b57", activeforeground="white", relief="flat",
                         bd=0, font=(UI_FONT, 9, "bold"), cursor="hand2", padx=18, pady=8,
                         highlightthickness=1, highlightbackground=OUTLINE)

    def drag_bind(self, widget: tk.Widget) -> None:
        widget.bind("<ButtonPress-1>", self.start_drag)
        widget.bind("<B1-Motion>", self.drag)

    def start_drag(self, event: tk.Event) -> None:
        self.drag_origin = (event.x_root - self.root.winfo_x(), event.y_root - self.root.winfo_y())
        self.drag_moved = False

    def drag(self, event: tk.Event) -> None:
        if self.drag_origin:
            if abs(event.x_root - self.root.winfo_x() - self.drag_origin[0]) > 2 or abs(
                    event.y_root - self.root.winfo_y() - self.drag_origin[1]) > 2:
                self.drag_moved = True
            x = event.x_root - self.drag_origin[0]
            y = event.y_root - self.drag_origin[1]
            self.root.geometry(f"+{x}+{y}")
            if self.bubble_mode:
                self.bubble_geometry = f"68x68+{x}+{y}"

    def clear_page(self) -> None:
        for child in self.page.winfo_children():
            child.destroy()

    def show_list_page(self) -> None:
        self.clear_page()
        self.make_header("Your tasks", "You are doing your best, and that is okay.")
        content = tk.Frame(self.page, bg=PANEL)
        content.pack(fill="both", expand=True)
        tabs = tk.Frame(content, bg=PANEL)
        tabs.pack(fill="x", padx=14, pady=(11, 6))
        for label in ("Today", "Upcoming", "All", "Done"):
            selected = self.view_mode.get() == label
            button = tk.Button(tabs, text=label, command=lambda mode=label: self.change_view(mode),
                               bg=(BG if selected else PANEL), fg=TEXT,
                               activebackground=MINT, activeforeground=TEXT,
                               relief="flat", bd=0, padx=9, pady=6,
                               font=(UI_FONT, 8, "bold" if selected else "normal"),
                               highlightthickness=1, highlightbackground=OUTLINE,
                               cursor="hand2")
            button.pack(side="left", padx=(0, 4))
        toolbar = tk.Frame(content, bg=PANEL)
        toolbar.pack(fill="x", padx=17, pady=(0, 4))
        self.summary = tk.Label(toolbar, text="", bg=PANEL, fg=MUTED,
                                font=(UI_FONT, 8), anchor="w")
        self.summary.pack(side="left")
        self.sort_box = ttk.Combobox(toolbar, textvariable=self.sort_mode,
                                     values=("Sort", "Priority"), state="readonly", width=10)
        self.sort_box.pack(side="right")
        self.sort_box.bind("<<ComboboxSelected>>", lambda _event: self.render_tasks())

        list_shell = tk.Frame(content, bg=PANEL)
        list_shell.pack(fill="both", expand=True, padx=14, pady=(4, 4))
        self.canvas = tk.Canvas(list_shell, bg=PANEL, highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(list_shell, orient="vertical", command=self.canvas.yview,
                                 bg=PANEL, troughcolor=PANEL, activebackground="#b8c9c2", width=7)
        self.list_frame = tk.Frame(self.canvas, bg=PANEL)
        self.list_frame.bind("<Configure>", lambda _event: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        self.canvas.bind("<Configure>", lambda event: self.canvas.itemconfigure(
            self.canvas_window, width=event.width))
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.canvas.bind_all("<MouseWheel>", self.on_wheel)

        bottom = tk.Frame(content, bg=PANEL)
        bottom.pack(fill="x", padx=17, pady=(4, 15))
        self.text_button(bottom, "Show completed" if not self.show_done.get() else "Hide completed",
                         self.toggle_show_done, bg=PANEL, size=8).pack(side="left")
        self.primary_button(bottom, "＋  Add task", self.show_form_page).pack(side="right")
        self.render_tasks()

    def change_view(self, mode: str) -> None:
        self.view_mode.set(mode)
        self.show_list_page()

    def toggle_show_done(self) -> None:
        self.show_done.set(not self.show_done.get())
        self.show_list_page()

    def show_form_page(self) -> None:
        self.clear_page()
        self.make_header("What needs doing?", "Add a task to your list", back=True)
        body = tk.Frame(self.page, bg=BG, padx=17, pady=18)
        body.pack(fill="both", expand=True)
        card = tk.Frame(body, bg=PANEL, padx=17, pady=16,
                        highlightthickness=1, highlightbackground=OUTLINE)
        card.pack(fill="x")

        tk.Label(card, text="Task", bg=PANEL, fg=TEXT,
                 font=(UI_FONT, 9, "bold")).pack(anchor="w")
        self.task_entry = tk.Entry(card, textvariable=self.title_var, bg=PANEL, fg=TEXT,
                                   insertbackground=TEXT, relief="flat", font=(UI_FONT, 10),
                                   highlightthickness=1, highlightbackground=OUTLINE)
        self.task_entry.pack(fill="x", ipady=8)
        tk.Frame(card, bg=OUTLINE, height=1).pack(fill="x", pady=(0, 14))
        self.task_entry.bind("<Return>", lambda _event: self.add_task())

        tk.Label(card, text="Due date", bg=PANEL, fg=TEXT,
                 font=(UI_FONT, 9, "bold")).pack(anchor="w")
        date_row = tk.Frame(card, bg=PANEL)
        date_row.pack(fill="x", pady=(5, 13))
        self.date_entry = tk.Entry(date_row, textvariable=self.date_var, state="readonly",
                                   readonlybackground=PANEL_ALT, fg=TEXT, relief="flat",
                                   font=(UI_FONT, 9), highlightthickness=1,
                                   highlightbackground=OUTLINE)
        self.date_entry.pack(side="left", fill="x", expand=True, ipady=7)
        self.text_button(date_row, "Choose date", self.show_date_picker,
                         bg=PANEL, size=8).pack(side="left", padx=(7, 0))

        tk.Label(card, text="Priority", bg=PANEL, fg=TEXT,
                 font=(UI_FONT, 9, "bold")).pack(anchor="w")
        self.priority_box = ttk.Combobox(card, textvariable=self.priority_var,
                                         values=("High", "Medium", "Low"),
                                         state="readonly", width=12)
        self.priority_box.pack(anchor="w", pady=(5, 15), ipady=4)

        tk.Label(card, text="Card color", bg=PANEL, fg=TEXT,
                 font=(UI_FONT, 9, "bold")).pack(anchor="w", pady=(0, 8))
        swatches = tk.Frame(card, bg=PANEL)
        swatches.pack(anchor="w", pady=(0, 14))
        for color in PASTELS:
            border = TEXT if self.color_var.get() == color else PANEL
            swatch = tk.Button(swatches, text="✓" if border == TEXT else "", width=2,
                               command=lambda value=color: self.select_color(value),
                               bg=color, activebackground=color, fg=TEXT,
                               relief="flat", bd=0, highlightthickness=2,
                               highlightbackground=border, cursor="hand2")
            swatch.pack(side="left", padx=(0, 7), ipadx=3, ipady=6)

        self.primary_button(body, "Save task", self.add_task).pack(pady=(15, 0), ipadx=24)
        self.task_entry.focus_set()

    def show_date_picker(self, task_id: str | None = None,
                         anchor: tk.Widget | None = None) -> None:
        if self.date_picker_window is not None and self.date_picker_window.winfo_exists():
            self.date_picker_window.lift()
            return

        task = next((item for item in self.tasks if item.get("id") == task_id), None)
        current_due = task.get("due", "") if task is not None else self.date_var.get()
        try:
            selected_date = datetime.strptime(current_due, "%Y-%m-%d").date()
        except ValueError:
            selected_date = date.today()
        month = date(selected_date.year, selected_date.month, 1)

        popup = tk.Toplevel(self.root)
        self.date_picker_window = popup
        popup.title("Choose due date")
        popup.configure(bg=PANEL)
        popup.resizable(False, False)
        popup.attributes("-topmost", True)
        popup.transient(self.root)
        popup.protocol("WM_DELETE_WINDOW", popup.destroy)

        shell = tk.Frame(popup, bg=PANEL, padx=12, pady=10,
                         highlightthickness=1, highlightbackground=OUTLINE)
        shell.pack(fill="both", expand=True)
        heading = tk.Frame(shell, bg=PANEL)
        heading.pack(fill="x", pady=(0, 8))
        month_label = tk.Label(heading, bg=PANEL, fg=TEXT,
                               font=(UI_FONT, 10, "bold"))
        month_label.pack(side="left", expand=True)
        calendar_grid = tk.Frame(shell, bg=PANEL)
        calendar_grid.pack()

        def render_month(value: date) -> None:
            for child in calendar_grid.winfo_children():
                child.destroy()
            month_label.configure(text=value.strftime("%B %Y"))
            for column, weekday in enumerate(("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")):
                tk.Label(calendar_grid, text=weekday, bg=PANEL, fg=MUTED,
                         font=(UI_FONT, 8, "bold"), width=4).grid(row=0, column=column)
            for row, week in enumerate(calendar.monthcalendar(value.year, value.month), start=1):
                for column, day_number in enumerate(week):
                    if not day_number:
                        tk.Label(calendar_grid, text="", bg=PANEL, width=4).grid(row=row, column=column)
                        continue
                    day_date = date(value.year, value.month, day_number)
                    is_selected = day_date == selected_date
                    is_today = day_date == date.today()
                    color = PASTELS[4] if is_selected else (PANEL_ALT if is_today else PANEL)
                    tk.Button(
                        calendar_grid, text=str(day_number), width=3, bg=color,
                        activebackground=PASTELS[4], fg=TEXT, relief="flat", bd=0,
                        font=(UI_FONT, 8), cursor="hand2",
                        command=lambda chosen=day_date: choose(chosen),
                    ).grid(row=row, column=column, padx=1, pady=1, ipady=3)

        def change_month(offset: int) -> None:
            nonlocal month
            month_index = month.year * 12 + month.month - 1 + offset
            year, zero_month = divmod(month_index, 12)
            month_next = date(year, zero_month + 1, 1)
            month = month_next
            render_month(month)

        def choose(chosen: date) -> None:
            save_due_date(chosen.isoformat())

        self.text_button(heading, "‹", lambda: change_month(-1), bg=PANEL, size=11).pack(side="left")
        self.text_button(heading, "›", lambda: change_month(1), bg=PANEL, size=11).pack(side="right")
        render_month(month)

        footer = tk.Frame(shell, bg=PANEL)
        footer.pack(fill="x", pady=(8, 0))
        self.text_button(footer, "Today", lambda: choose(date.today()), bg=PANEL, size=8).pack(side="left")
        self.text_button(footer, "Clear date", lambda: clear_date(), bg=PANEL, size=8).pack(side="right")

        def clear_date() -> None:
            save_due_date("")

        def save_due_date(value: str) -> None:
            if task_id is None:
                self.date_var.set(value)
            else:
                matching_task = next((item for item in self.tasks
                                      if item.get("id") == task_id), None)
                if matching_task is not None:
                    matching_task["due"] = value
                    self.save_tasks()
                    self.render_tasks()
            popup.destroy()
            self.date_picker_window = None

        popup.update_idletasks()
        anchor = anchor or self.date_entry
        x = anchor.winfo_rootx()
        y = anchor.winfo_rooty() + anchor.winfo_height() + 4
        popup.geometry(f"+{x}+{y}")
        popup.grab_set()
        popup.focus_force()

    def select_color(self, value: str) -> None:
        self.color_var.set(value)
        self.show_form_page()

    def add_task(self) -> None:
        title = self.title_var.get().strip()
        if not title:
            self.task_entry.focus_set()
            return
        due = self.date_var.get().strip()
        if due:
            try:
                datetime.strptime(due, "%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Check the due date", "Enter a date as YYYY-MM-DD, for example 2026-10-30.", parent=self.root)
                return
        self.tasks.append({"id": uuid.uuid4().hex, "title": title, "due": due,
                           "priority": self.priority_var.get(), "color": self.color_var.get(),
                           "done": False})
        self.save_tasks()
        self.title_var.set("")
        self.date_var.set("")
        self.view_mode.set("All")
        self.show_list_page()

    def toggle_done(self, task_id: str) -> None:
        for task in self.tasks:
            if task.get("id") == task_id:
                task["done"] = not task.get("done", False)
                break
        self.save_tasks()
        self.render_tasks()

    def delete_task(self, task_id: str) -> None:
        self.tasks = [task for task in self.tasks if task.get("id") != task_id]
        self.save_tasks()
        self.render_tasks()

    def due_label(self, due: str) -> tuple[str, str]:
        if not due:
            return "No due date", MUTED
        try:
            delta = (date.fromisoformat(due) - date.today()).days
        except ValueError:
            return due, MUTED
        if delta < 0:
            return f"Overdue · {abs(delta)}d", RED
        if delta == 0:
            return "Due today", RED
        if delta == 1:
            return "Due tomorrow", YELLOW
        return f"Due {due}", MUTED

    def task_sort_key(self, task: dict) -> tuple:
        due = task.get("due", "") or "9999-12-31"
        rank = {"High": 0, "Medium": 1, "Low": 2}.get(task.get("priority"), 1)
        if self.sort_mode.get() == "Priority":
            return (bool(task.get("done")), rank, due, task.get("title", "").lower())
        return (bool(task.get("done")), due, rank, task.get("title", "").lower())

    def in_current_view(self, task: dict) -> bool:
        mode = self.view_mode.get()
        is_done = bool(task.get("done", False))
        if mode == "Done":
            return is_done
        if is_done and not self.show_done.get():
            return False
        due = task.get("due", "")
        if mode == "Today":
            return due == date.today().isoformat()
        if mode == "Upcoming":
            if not due:
                return False
            try:
                delta = (date.fromisoformat(due) - date.today()).days
                return delta > 0
            except ValueError:
                return False
        return True

    def render_tasks(self) -> None:
        if not hasattr(self, "list_frame") or not self.list_frame.winfo_exists():
            return
        for child in self.list_frame.winfo_children():
            child.destroy()
        visible = [task for task in self.tasks if self.in_current_view(task)]
        visible.sort(key=self.task_sort_key)
        self.summary.configure(text=f"{len(visible)} {'task' if len(visible) == 1 else 'tasks'}")
        if not visible:
            empty = "Nothing due today." if self.view_mode.get() == "Today" else "All clear. Add a task when you need it."
            tk.Label(self.list_frame, text=empty, bg=PANEL, fg=MUTED,
                     font=(UI_FONT, 9), pady=25).pack(fill="x")
            return
        for task in visible:
            self.draw_task(task)

    def draw_task(self, task: dict) -> None:
        done = bool(task.get("done", False))
        fallback = {"High": PASTELS[5], "Medium": PASTELS[1], "Low": PASTELS[3]}
        color = task.get("color") or fallback.get(task.get("priority"), PASTELS[0])
        if color not in PASTELS:
            color = fallback.get(task.get("priority"), PASTELS[0])
        card = tk.Frame(self.list_frame, bg=color, padx=9, pady=9,
                        highlightthickness=1, highlightbackground=OUTLINE)
        card.pack(fill="x", pady=(0, 8))
        top = tk.Frame(card, bg=color)
        top.pack(fill="x")
        check = tk.Checkbutton(top, text="", command=lambda task_id=task.get("id"): self.toggle_done(task_id),
                               bg=color, activebackground=color, selectcolor="#ffffff",
                               fg="#527d6a", activeforeground="#527d6a", relief="flat", bd=0,
                               cursor="hand2")
        check.pack(side="left", padx=(0, 5))
        check.select() if done else check.deselect()
        title = tk.Label(top, text=task.get("title", "Untitled"), bg=color,
                         fg=(MUTED if done else TEXT), font=(UI_FONT, 9, "bold"),
                         anchor="w", justify="left", wraplength=255)
        title.pack(side="left", fill="x", expand=True)
        self.text_button(top, "×", lambda task_id=task.get("id"): self.delete_task(task_id),
                         bg=color, size=12).pack(side="right")
        meta = tk.Frame(card, bg=color)
        meta.pack(fill="x", padx=(29, 0), pady=(3, 0))
        due_text, _due_color = self.due_label(task.get("due", ""))
        due_label = tk.Label(meta, text=f"◷  {due_text}", bg=color, fg=MUTED,
                             font=(UI_FONT, 8, "underline"), cursor="hand2")
        due_label.pack(side="left")
        due_label.bind("<Button-1>", lambda _event, task_id=task.get("id"),
                       widget=due_label: self.show_date_picker(task_id, widget))
        due_label.bind("<Enter>", lambda _event: due_label.configure(fg=TEXT))
        due_label.bind("<Leave>", lambda _event: due_label.configure(fg=MUTED))
        priority = task.get("priority", "Medium")
        pcolor = {"High": "#bd5560", "Medium": "#946c16", "Low": "#41805f"}.get(priority, MUTED)
        tk.Label(meta, text=f"● {priority}", bg=color, fg=pcolor,
                 font=(UI_FONT, 8, "bold")).pack(side="right")

    def on_wheel(self, event: tk.Event) -> None:
        if not self.bubble_mode and hasattr(self, "canvas") and self.canvas.winfo_exists():
            self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def play_minimize_sound(self) -> None:
        sound_path = Path(__file__).with_name("close.wav")
        if winsound is not None and sound_path.is_file():
            try:
                winsound.PlaySound(str(sound_path), winsound.SND_FILENAME | winsound.SND_ASYNC)
            except (OSError, RuntimeError):
                pass

    def shape_bubble_window(self, window: tk.Toplevel) -> None:
        """Clip the minimized widget to a circle using the native Windows region."""
        try:
            gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            gdi32.CreateEllipticRgn.argtypes = (ctypes.c_int, ctypes.c_int,
                                                 ctypes.c_int, ctypes.c_int)
            gdi32.CreateEllipticRgn.restype = ctypes.c_void_p
            gdi32.DeleteObject.argtypes = (ctypes.c_void_p,)
            gdi32.DeleteObject.restype = wintypes.BOOL
            user32.SetWindowRgn.argtypes = (wintypes.HWND, ctypes.c_void_p, wintypes.BOOL)
            user32.SetWindowRgn.restype = ctypes.c_int
            region = gdi32.CreateEllipticRgn(0, 0, 68, 68)
            if region and not user32.SetWindowRgn(window.winfo_id(), region, True):
                gdi32.DeleteObject(region)
        except (AttributeError, OSError, tk.TclError):
            pass

    def collapse(self, play_sound: bool = True) -> None:
        if self.bubble_mode:
            return
        self.root.update_idletasks()
        self.normal_geometry = self.root.geometry()
        self.bubble_geometry = self.corner_geometry(68, 68, margin=8)
        if play_sound:
            self.play_minimize_sound()
        self.bubble_mode = True
        self.root.unbind_all("<MouseWheel>")
        bubble = tk.Toplevel(self.root)
        self.bubble_window = bubble
        bubble.overrideredirect(True)
        bubble.attributes("-topmost", True)
        # Windows Tk supports a color key for transparent pixels. Keep it
        # different from the mint circle so only the square canvas disappears.
        transparent_key = "#010203"
        bubble.configure(bg=transparent_key)
        try:
            bubble.attributes("-transparentcolor", transparent_key)
        except tk.TclError:
            pass
        bubble.geometry(self.bubble_geometry)
        canvas = tk.Canvas(bubble, width=68, height=68, bg=transparent_key,
                           highlightthickness=0, bd=0)
        self.bubble_canvas = canvas
        canvas.pack()
        count = sum(not task.get("done", False) for task in self.tasks)
        try:
            icon_path = Path(__file__).with_name("task_bubble_icon.png")
            self.bubble_icon = tk.PhotoImage(master=bubble, file=str(icon_path))
            canvas.create_image(34, 33, image=self.bubble_icon)
        except tk.TclError:
            self.bubble_icon = None
            canvas.create_text(34, 33, text="✦", fill="white", font=(UI_FONT, 22, "bold"))
        if count:
            canvas.create_oval(46, 0, 67, 21, fill=RED, outline=BG, width=2)
            canvas.create_text(56, 10, text=str(count) if count < 100 else "99+",
                              fill="white", font=(UI_FONT, 7, "bold"))
        canvas.bind("<Button-1>", lambda _event: self.expand())
        bubble.bind("<Button-1>", lambda _event: self.expand())
        bubble.protocol("WM_DELETE_WINDOW", self.expand)
        bubble.deiconify()
        bubble.lift()
        bubble.update_idletasks()
        self.shape_bubble_window(bubble)
        self.root.withdraw()

    def bubble_release(self, _event: tk.Event) -> None:
        if not self.drag_moved:
            self.expand()
        self.drag_origin = None

    def expand(self) -> None:
        if not self.bubble_mode:
            return
        bubble = self.bubble_window
        if bubble is not None and bubble.winfo_exists():
            bubble_x, bubble_y = bubble.winfo_x(), bubble.winfo_y()
            bubble.destroy()
        else:
            left, top, right, bottom = self.work_area()
            bubble_x, bubble_y = right - 68 - 8, bottom - 68 - 8
        self.bubble_window = None
        self.bubble_canvas = None
        left, top, right, bottom = self.work_area()
        panel_width, panel_height, margin = 400, 660, 12
        max_x = max(left + margin, right - panel_width - margin)
        max_y = max(top + margin, bottom - panel_height - margin)
        panel_x = min(max(left + margin, bubble_x + 68 - panel_width), max_x)
        panel_y = min(max(top + margin, bubble_y + 68 - panel_height), max_y)
        self.normal_geometry = f"{panel_width}x{panel_height}+{panel_x}+{panel_y}"
        self.bubble_mode = False
        self.root.geometry(self.normal_geometry)
        self.root.deiconify()
        self.root.lift()
        self.root.bind_all("<MouseWheel>", self.on_wheel)

    def quit_app(self) -> None:
        self.save_tasks()
        self.root.destroy()


if __name__ == "__main__":
    _mutex_handle, _already_running = acquire_single_instance()
    if _already_running:
        raise SystemExit(0)
    app_root = tk.Tk()
    TaskBubble(app_root)
    app_root._single_instance_mutex = _mutex_handle
    app_root.mainloop()
