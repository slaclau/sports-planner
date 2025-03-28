from typing import TYPE_CHECKING
import logging

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, Gio

if TYPE_CHECKING:
    from sports_planner.gui.app import Context

logger = logging.getLogger(__name__)


class FileInfo(Gtk.Box):
    def __init__(self, config_path: str, context: "Context"):
        super().__init__(
            margin_start=5, margin_end=5, orientation=Gtk.Orientation.VERTICAL
        )
        self.context = context
        self.context.connect("activity-changed", lambda _: self._update())
        self._update()

    def _update(self):
        logger.debug("updating")
        child = self.get_first_child()
        while child is not None:
            next = child.get_next_sibling()
            self.remove(child)
            child = next

        logger.debug("adding info")

        self.append(
            Gtk.Label(
                label=f"Activity name: {self.context.activity.name}",
                halign=Gtk.Align.START,
            )
        )
        self.append(
            Gtk.Label(
                label=f"Activity ID: {self.context.activity.activity_id}",
                halign=Gtk.Align.START,
                selectable=True,
            )
        )
        self.append(
            Gtk.Label(
                label=f"Importer: {self.context.activity.source}",
                halign=Gtk.Align.START,
                selectable=True,
            )
        )
        self.append(
            Gtk.Label(
                label=f"Activity file: {self.context.activity.original_file}",
                halign=Gtk.Align.START,
                wrap=True,
                selectable=True,
            )
        )

    def get_settings_pages(self):
        return []
