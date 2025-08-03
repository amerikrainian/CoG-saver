#!/usr/bin/env python3
"""CoG Saver - A save manager for Choice of Games titles."""

from __future__ import annotations

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


class ExtensionChecker:
    """File filter for .cogsav files."""

    @staticmethod
    def filter() -> str:
        """Return the file filter string for QFileDialog."""
        return "CoG Saver Files (*.cogsav)"


class CoGSaver(QMainWindow):
    """Main application window for CoG Saver."""

    def __init__(self) -> None:
        """Initialize the CoG Saver application."""
        super().__init__()
        self.settings = QSettings("CoGSaver", "CoGSaver")
        self.save_location: Path | None = None
        self.save_folder: Path | None = None
        self.quick_save_location: Path | None = None
        self.saves_list: list[Path] = []

        self._init_ui()
        self._load_preferences()
        self._update_game()

    def _init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle("CoG Saver")
        self.resize(600, 200)

        icon_path = Path("icon.gif")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        self.main_message = QListWidget()
        self.main_message.setAccessibleName("Status Messages")
        self.main_message.setAccessibleDescription(
            "List of status messages and notifications from the application. "
            "Use arrow keys to navigate through messages."
        )
        self.main_message.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        main_layout.addWidget(self.main_message)

        button_widget = QWidget()
        button_layout = QVBoxLayout(button_widget)
        button_grid = QGridLayout()
        button_layout.addLayout(button_grid)
        button_layout.addStretch()

        self.button_quicksave = QPushButton("Quicksave")
        self.button_quicksave.setAccessibleName("Quicksave")
        self.button_quicksave.setAccessibleDescription("Save current game state to quick save slot")
        self.button_quicksave.clicked.connect(self._quick_save)

        self.button_quickload = QPushButton("Quickload")
        self.button_quickload.setAccessibleName("Quickload")
        self.button_quickload.setAccessibleDescription("Load game state from quick save slot")
        self.button_quickload.clicked.connect(self._quick_load)

        self.button_save = QPushButton("Create save")
        self.button_save.setAccessibleName("Create save")
        self.button_save.setAccessibleDescription(
            "Create a new named save file with current game state"
        )
        self.button_save.clicked.connect(self._create_perm_save)

        self.button_load = QPushButton("Load Save")
        self.button_load.setAccessibleName("Load Save")
        self.button_load.setAccessibleDescription("Load a previously created save file")
        self.button_load.clicked.connect(self._load_perm_save)

        self.button_change_game = QPushButton("Select Game")
        self.button_change_game.setAccessibleName("Select Game")
        self.button_change_game.setAccessibleDescription("Select the game save file location")
        self.button_change_game.clicked.connect(self._change_game)

        button_grid.addWidget(self.button_quicksave, 0, 0)
        button_grid.addWidget(self.button_quickload, 1, 0)
        button_grid.addWidget(self.button_save, 2, 0)
        button_grid.addWidget(self.button_load, 3, 0)
        button_grid.addWidget(self.button_change_game, 4, 0)

        main_layout.addWidget(button_widget)

    def _append_message(self, msg: str) -> None:
        """Append a timestamped message to the message list."""
        timestamp = datetime.now().strftime("%H:%M:%S")  # noqa: DTZ005
        # Replace newlines with spaces for better screen reader experience
        # but preserve the visual formatting intent
        formatted_msg = msg.replace("\n", " ")
        item = QListWidgetItem(f"[{timestamp}] {formatted_msg}")
        self.main_message.addItem(item)
        self.main_message.scrollToItem(item)

    def _load_preferences(self) -> None:
        """Load saved preferences."""
        save_location_str = self.settings.value("saveLocation", type=str)
        if save_location_str:
            self.save_location = Path(save_location_str)

    def _update_game(self) -> None:
        """Update game-related paths and load save files."""
        if self.save_location and self.save_location.exists():
            try:
                self.save_location = self.save_location.resolve()
                self.save_folder = self.save_location.parent / "saves"
                self.save_folder.mkdir(exist_ok=True)
                self._append_message(f"Custom saves directory: {self.save_folder}")

                self.quick_save_location = self.save_location.parent / "quicksave.cogsav"
                self._append_message(f"Quicksave file: {self.quick_save_location}")

                self._generate_saves_list()
            except OSError as e:
                self._append_message(f"Error: {e}")
                self._append_message(f"Failed to use {self.save_location} as a base file!")
        else:
            self._append_message(
                "No game selected! Please select a save file location by\n"
                '    clicking "Select Game" and choosing a\n'
                "    storePS<gamename>PSstate file!"
            )

    def _generate_saves_list(self) -> None:
        """Generate list of save files in the saves folder."""
        if self.save_folder and self.save_folder.exists():
            self.saves_list = list(self.save_folder.glob("*.cogsav"))
            for save_file in self.saves_list:
                self._append_message(f"Found file: {save_file.name}")
            self._append_message(f"Found {len(self.saves_list)} files.")

    def _change_game(self) -> None:
        """Let user select a game save file."""
        initial_dir = str(self.save_location.parent) if self.save_location else ""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select a 'storePS<gamename>PSstate' file:",
            initial_dir,
            "All Files (*)",
        )

        if file_path:
            selected_file = Path(file_path)
            self._append_message(f"Selected {selected_file}")

            if selected_file.name.endswith("PSstate"):
                self.save_location = selected_file
                self.settings.setValue("saveLocation", str(self.save_location))
                self._update_game()
                self.setWindowTitle(f"CoG Saver - {selected_file.name}")
            else:
                self.save_location = None
                self._append_message(
                    "\n\n"
                    "ERROR: Please select only a 'storePS<gamename>PSstate' file.\n"
                    "This file may be found in:\n"
                    "'\\Steam\\userdata\\<yourSteamID#>\\<SteamGame#>\\remote'\n"
                    'The file selected MUST be the one that ends with "PSstate" only!'
                )

    def _quick_save(self) -> None:
        """Copy current steam save to the quicksave slot."""
        if not self.save_location:
            self._append_message(
                "ERROR! Please select your game's save file by clicking 'Select Game'"
            )
            return

        try:
            if self.quick_save_location:
                shutil.copy2(self.save_location, self.quick_save_location)
                self._append_message("Quicksaved")
        except OSError as e:
            self._append_message(f"Error: {e}")
            self._append_message("Quicksave failed")

    def _quick_load(self) -> None:
        """Copy current quicksave to the steam save slot."""
        if not self.save_location:
            self._append_message(
                "ERROR! Please select your game's save file by clicking 'Select Game'"
            )
            return

        try:
            if self.quick_save_location and self.quick_save_location.exists():
                shutil.copy2(self.quick_save_location, self.save_location)
                self._append_message("Loaded")
            else:
                self._append_message("No quicksave found")
        except OSError as e:
            self._append_message(f"Error: {e}")
            self._append_message("Load failed")

    def _parse_save(self) -> str:
        """Parse save file to extract character name and scene."""
        self._append_message("Parsing current save...")
        name = None
        scene = None

        if not self.save_location:
            return datetime.now().strftime("%y.%m.%d %H.%M")  # noqa: DTZ005

        try:
            with self.save_location.open("r", encoding="utf-8") as f:
                content = f.read()

            name_match = re.search(r'"(?:name|firstname)"\s*:\s*"([^"]+)"', content)
            if name_match:
                name = name_match.group(1)

            scene_match = re.search(r'"sceneName"\s*:\s*"([^"]+)"', content)
            if scene_match:
                scene = scene_match.group(1)

        except OSError as e:
            self._append_message(f"Error parsing save: {e}")

        timestamp = datetime.now().strftime("%y.%m.%d %H.%M")  # noqa: DTZ005
        parts = []
        if name:
            parts.append(name)
        parts.append(timestamp)
        if scene:
            parts.append(scene)

        return_val = " ".join(parts)
        self._append_message(return_val)
        return return_val

    def _create_perm_save(self) -> None:
        """Create a permanent save file."""
        if not self.save_location:
            self._append_message(
                "ERROR! Please select your game's save file by clicking 'Select Game'"
            )
            return

        suggested_name = self._parse_save()
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save game state",
            str(self.save_folder / suggested_name) if self.save_folder else suggested_name,
            ExtensionChecker.filter(),
        )

        if save_path:
            save_file = Path(save_path)
            if not save_file.suffix:
                save_file = save_file.with_suffix(".cogsav")

            try:
                shutil.copy2(self.save_location, save_file)
                self._append_message(f"Saved to {save_file}")
            except OSError as e:
                self._append_message(f"Error: {e}")
                self._append_message("Save failed")

    def _load_perm_save(self) -> None:
        """Load a permanent save file."""
        if not self.save_location:
            self._append_message(
                "ERROR! Please select your game's save file by clicking 'Select Game'"
            )
            return

        save_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load save file",
            str(self.save_folder) if self.save_folder else "",
            f"{ExtensionChecker.filter()};;All Files (*)",
        )

        if save_path:
            save_file = Path(save_path)
            try:
                shutil.copy2(save_file, self.save_location)
                display_path = save_file
                if self.save_folder and self.save_folder in save_file.parents:
                    display_path = save_file.relative_to(self.save_folder.parent)
                self._append_message(f"Loaded: {display_path}")
            except OSError as e:
                self._append_message(f"Error: {e}")
                self._append_message("Error loading save")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CoG Saver application."""
    app = QApplication(list(argv) if argv else [])
    app.setApplicationName("CoG Saver")
    app.setOrganizationName("CoGSaver")

    window = CoGSaver()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
