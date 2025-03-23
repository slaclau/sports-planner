import logging
from typing import TYPE_CHECKING

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, Gtk, Gio, GObject, GLib

from sports_planner.gui.activities.overview.metrics_list import MetricsList
from sports_planner.gui.activities.overview.metric import Metric
from sports_planner.gui.activities.overview.chart import Chart

if TYPE_CHECKING:
    from sports_planner.gui.activities.overview.overview import _Overview

logger = logging.getLogger(__name__)

tile_type_map = {"metrics-list": MetricsList, "metric": Metric, "chart": Chart}


class Tile(Gtk.Frame):
    _start_column = 0
    _columns = 0
    _height = 0

    @GObject.Signal
    def removed(self):
        logger.debug("removed")

    def __init__(self, id: str, overview: "_Overview"):
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

        self.box.append(self.child)

        # self._add_controllers()

    def _add_controllers(self):
        click_controller = Gtk.GestureClick()
        click_controller.set_button(1)
        click_controller.connect("pressed", self._on_click)
        self.add_controller(click_controller)

        motion_controller = Gtk.EventControllerMotion()
        motion_controller.connect("enter", self._on_motion)
        motion_controller.connect("motion", self._on_motion)
        motion_controller.connect(
            "leave", lambda _: self.set_cursor_from_name("default")
        )

        self.add_controller(motion_controller)

    def _on_click(self, gesture, n_press, x, y):
        state = gesture.get_current_event_state()
        width = self.get_width()
        height = self.get_height()

        if width - x < 8:
            return

        if height - y < 8:
            return

    def _on_motion(self, controller, x, y):
        width = self.get_width()
        height = self.get_height()

        if width - x < 8:
            self.set_cursor_from_name("e-resize")
            return

        if height - y < 8:
            self.set_cursor_from_name("s-resize")
            return

        self.set_cursor_from_name("default")

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
        type_row = Adw.ComboRow(
            title="Type",
        )
        types = ["metric", "metrics-list", "chart"]
        types_list = Gtk.StringList(strings=types)
        type_row.set_model(types_list)
        type_row.set_selected(types.index(self.settings.get_string("type")))
        type_row.connect(
            "notify::selected-item",
            lambda w, s: self.settings.set_string(
                "type", w.get_selected_item().get_string()
            ),
        )

        self.settings.bind("title", title_row, "text", Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind("columns", width_row, "value", Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind("height", height_row, "value", Gio.SettingsBindFlags.DEFAULT)

        basic_group.add(title_row)
        basic_group.add(width_row)
        basic_group.add(height_row)
        basic_group.add(type_row)

        dangerous_group = Adw.PreferencesGroup(title="Dangerous settings")
        basic_page.add(dangerous_group)

        remove_row = Adw.ButtonRow(title="Remove tile")
        remove_row.connect("activated", lambda _: self.emit("removed"))
        remove_row.add_css_class("destructive-action")
        dangerous_group.add(remove_row)

        for page in self.child.get_settings_pages():
            dialog.add(page)

        self.settings.connect("changed::type", lambda _, __: dialog.close())

        dialog.present(self)
