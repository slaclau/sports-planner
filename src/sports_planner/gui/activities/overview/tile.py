import logging
from typing import TYPE_CHECKING

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, Gtk, Gio, GObject

from sports_planner.gui.activities.overview.metrics_list import MetricsList

if TYPE_CHECKING:
    from sports_planner.gui.activities.overview.overview import Overview


class Tile(Gtk.Frame):
    _start_column = 0
    _columns = 0
    _height = 0

    def __init__(self, id: str, overview: "Overview"):
        self._start_column: int
        self._columns: int
        self._height: int

        super().__init__()
        config_path = f"/io/github/slaclau/sports-planner/views/activities/tabs/{overview.name}/tiles/{id}/"
        self.settings = Gio.Settings(
            schema_id="io.github.slaclau.sports-planner.views.activities.tabs.overview.tile",
            path=config_path,
        )
        tile_type = self.settings.get_string("type")
        self.id = id

        self.settings.bind(
            "start-column", self, "start_column", Gio.SettingsBindFlags.DEFAULT
        )
        self.settings.bind("columns", self, "columns", Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind("height", self, "height", Gio.SettingsBindFlags.DEFAULT)

        self.add_controller(Gtk.DragSource())
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(self.box)
        self.title_label = Gtk.Label()
        self.settings.bind(
            "title", self.title_label, "label", Gio.SettingsBindFlags.DEFAULT
        )
        self.box.append(self.title_label)
        if tile_type == "metrics-list":
            self.box.append(MetricsList(config_path, tile_type, overview.context))
        else:
            raise ValueError(f"Unknown tile type {tile_type}")

    @GObject.Property(type=int)
    def start_column(self):
        return self._start_column

    @start_column.setter
    def start_column(self, value):
        self._start_column = value

    @GObject.Property(type=int)
    def columns(self):
        return self._columns

    @columns.setter
    def columns(self, value):
        self._columns = value

    @GObject.Property(type=int)
    def height(self):
        return self._height

    @height.setter
    def height(self, value):
        self._height = value
