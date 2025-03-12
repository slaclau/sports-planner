from typing import TYPE_CHECKING

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, Gtk, Gio, GObject, GLib

from sports_planner.gui.activities.overview.metrics_list import MetricsList
from sports_planner.gui.activities.overview.metric import Metric

if TYPE_CHECKING:
    from sports_planner.gui.activities.overview.overview import Overview

tile_type_map = {"metrics-list": MetricsList, "metric": Metric}


class Tile(Gtk.Frame):
    _start_column = 0
    _columns = 0
    _height = 0

    def __init__(self, id: str, overview: "Overview"):
        self._start_column: int
        self._columns: int
        self._height: int

        super().__init__()
        self.add_css_class("card")

        config_path = f"/io/github/slaclau/sports-planner/views/activities/tabs/{overview.name}/tiles/{id}/"
        self.settings = Gio.Settings(
            schema_id="io.github.slaclau.sports-planner.views.activities.tabs.overview.tile",
            path=config_path,
        )
        tile_type = self.settings.get_string("type")
        self.id = id
        self.overview = overview

        self.settings.bind(
            "start-column", self, "start_column", Gio.SettingsBindFlags.DEFAULT
        )
        self.settings.bind("columns", self, "columns", Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind("height", self, "height", Gio.SettingsBindFlags.DEFAULT)

        self.add_controller(Gtk.DragSource())
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(self.box)
        self.title_label = Gtk.Label(
            hexpand=True, halign=Gtk.Align.START, margin_start=16
        )
        self.title_label.add_css_class("title-4")
        self.settings.bind(
            "title", self.title_label, "label", Gio.SettingsBindFlags.DEFAULT
        )
        self.title_box = Gtk.Box(hexpand=True)
        self.title_box.append(self.title_label)
        settings_button = Gtk.Button(icon_name="settings-symbolic")
        settings_button.connect("clicked", lambda b: self.show_settings())
        settings_button.add_css_class("flat")
        self.title_box.append(settings_button)

        self.box.append(self.title_box)
        self.child = tile_type_map[tile_type](config_path, overview.context)

        self.update_size_request()
        self.connect("notify::change", lambda p, v: self.update_size_request())
        self.box.append(self.child)

    def update_size_request(self):
        self.set_size_request(
            -1,
            self.overview.row_height * self.height
            + self.overview.row_spacing * (self.height - 1),
        )

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

    def show_settings(self):
        dialog = Adw.PreferencesDialog(
            title=f"{self.settings.get_string("title")} ({self.settings.get_string("type")}"
        )
        basic_page = Adw.PreferencesPage(
            title="Basic settings", icon_name="settings-symbolic"
        )
        dialog.add(basic_page)

        basic_group = Adw.PreferencesGroup(title="Basic settings")
        basic_page.add(basic_group)

        title_row = Adw.EntryRow(title="Title")
        width_row = Adw.SpinRow.new_with_range(1, self.overview.n_columns, 1)
        width_row.set_title("Width")
        height_row = Adw.SpinRow.new_with_range(1, 100, 1)
        height_row.set_title("Height")

        self.settings.bind("title", title_row, "text", Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind("columns", width_row, "value", Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind("height", height_row, "value", Gio.SettingsBindFlags.DEFAULT)

        basic_group.add(title_row)
        basic_group.add(width_row)
        basic_group.add(height_row)

        for page in self.child.get_settings_pages():
            dialog.add(page)

        dialog.present(self)
