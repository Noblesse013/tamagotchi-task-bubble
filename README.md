<p align="center">
  <img src="task_bubble_icon.png" alt="Task Bubble icon" width="128">
</p>

# Task Bubble

A lightweight Windows desktop task widget with a retro lavender UI. Keep tasks in an always-on-top panel or minimize to a cute Tamagotchi-style bubble in the bottom-right corner. Tasks are sorted by due date or priority and saved locally.

## Features

- **Two modes** – Full panel or minimized bubble
- **Smart filtering** – Tabs for `Today`, `Upcoming`, `All`, and `Done`
- **Flexible sorting** – Sort by due date or priority
- **Quick editing** – Click any due date to change or clear it directly from the list
- **Custom tasks** – Set due dates, priorities, and pastel colors
- **Local storage** – All tasks stay on your PC
- **Auto-start** – Can launch on Windows sign-in

## Screenshots

| Empty Today Tab | Add Task Form | Minimized Bubble |
| --- | --- | --- |
| ![Task Bubble empty Today tab](assets/Screenshot%202026-10-25%20150157.png) | ![Task Bubble add task form](assets/Screenshot%202026-10-25%20150222.png) | ![Task Bubble minimized bubble mode](assets/Screenshot%202026-10-25%20150440.png) |

![Task Bubble screenshot](assets/Screenshot%202026-10-27%20221309.png)

## Installation

### Option 1: Download from Releases (Recommended)
1. Go to the [GitHub Releases](https://github.com/Noblesse013/tamagotchi-task-bubble/releases) page and download the latest `TaskBubble-*-windows-x64.zip`.
2. Extract the ZIP to a folder of your choice.
3. Right-click `install.ps1` → **Run with PowerShell**.  
   If Windows blocks execution, open PowerShell in that folder and run:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
   ```

### Option 2: Clone with Git
```powershell
git clone https://github.com/Noblesse013/tamagotchi-task-bubble.git
cd tamagotchi-task-bubble
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

### Option 3: Run from Source
1. Install [Python 3.10+](https://www.python.org/downloads/) for Windows.
2. Clone or download this repository.
3. Run the app:

   ```powershell
   python task_bubble.pyw
   ```

**What the installer does:**
- Installs to `%LOCALAPPDATA%\Programs\TaskBubble` (no admin rights required)
- Creates a desktop shortcut
- Adds to Windows Startup
- Launches the app after installation

**Uninstall:** Run `uninstall.ps1` from the extracted folder. Your tasks remain saved at `%LOCALAPPDATA%\TaskBubble\tasks.json`.

## Usage

- **Add a task:** Click `+ Add task`, pick a due date (or `Clear date`), set priority and color, then save.
- **Edit due dates:** Click the underlined due date on any task card (including `No due date`) to change or clear it.
- **Filter & sort:** Use `Today` / `Upcoming` / `All` / `Done` tabs and the sort dropdown.
- **Move:** Drag the top bar to reposition the panel.
- **Bubble mode:** Click `^` to minimize to the bubble. Click the bubble to reopen. A short chime plays when minimizing.
- **Close:** Click `×` to quit.

## Design & Data

- **Storage:** `%LOCALAPPDATA%\TaskBubble\tasks.json`
- **Theme:** Lavender retro look with cream panels, pixel outlines, Courier New text, pastel task cards. Bubble shows the Tamagotchi icon with a badge for unfinished tasks.

## Build a Standalone EXE

```powershell
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed --name TaskBubble --icon task_bubble.ico --add-data "task_bubble_icon.png;." --add-data "task_bubble.ico;." --add-data "close.wav;." task_bubble.pyw
```

Releases are built automatically via GitHub Actions when a version tag (e.g. `v1.0.0`) is pushed.

## License

Task Bubble is open source under the [MIT License](LICENSE).
