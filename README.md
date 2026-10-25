# Task Bubble

Task Bubble is a small Windows desktop task widget. Keep a lavender retro task panel open above other windows, or minimize it to the Tamagotchi bubble in the bottom-right corner. Tasks are sorted by due date or priority and saved on your computer.

## Install on Windows

### From a release

1. Download the latest `TaskBubble-...-windows-x64.zip` from the project's GitHub Releases page and extract it.
2. Right-click `install.ps1` and choose **Run with PowerShell**. If Windows blocks the script, open PowerShell in the extracted folder and run:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
   ```

The installer needs no administrator access. It installs Task Bubble under `%LOCALAPPDATA%\Programs\TaskBubble`, adds a desktop shortcut, and starts the app when you sign in to Windows. Run `uninstall.ps1` from the extracted folder to remove the app and its shortcuts. Your saved tasks are kept.

### From source

Install Python 3.10 or newer for Windows, download or clone this repository, then run `install.ps1` as above. The installer creates the same shortcuts and sign-in startup entry. To remove them and the installed app, run `uninstall.ps1`.

## Use it

- Select **＋ Add task** to add a task, choose an optional due date from the calendar, set its priority, and pick a card color. Use **Clear date** for tasks without a deadline.
- Click a task card's underlined due-date line (including **No due date**) to change or clear its date directly from the list.
- Use Today, Upcoming, All, and Done to filter tasks; sort by due date or priority.
- Drag the top bar to move the panel. Minimize it to the bubble and click the bubble to reopen the panel.
- Click **×** to quit. A short chime plays when minimizing.

Tasks are stored locally at `%LOCALAPPDATA%\TaskBubble\tasks.json`. Uninstalling does not delete this file.

## UI design

Task Bubble uses a lavender, old-school desktop look. The task panel pairs a pale lavender surround with warm cream surfaces, dark pixel-like outlines, Courier New labels, and soft pastel task cards. The floating state uses the Tamagotchi artwork by itself, with a small badge for unfinished tasks and no colored halo behind it.

![Task Bubble task list](assets/task-bubble-ui.png)

The screenshot shows the current task-list panel. The add-task form includes a clickable calendar date picker, priority selector, and pastel color choices. The current bubble artwork is `task_bubble_icon.png`.

## Build a standalone Windows executable

The project includes a GitHub Actions workflow that builds a single-file, windowed Windows executable when a version tag such as `v1.0.0` is pushed. It packages the icon and chime and attaches a ZIP with the installer scripts to the GitHub Release. To build locally, install Python 3.10+ and run:

```powershell
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed --name TaskBubble --icon task_bubble.ico --add-data "task_bubble_icon.png;." --add-data "task_bubble.ico;." --add-data "close.wav;." task_bubble.pyw
```

## License

Task Bubble is open source under the MIT License. See [LICENSE](LICENSE).
