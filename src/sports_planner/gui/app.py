import importlib.resources
from importlib.metadata import version
import logging
import sys
import enum
import time

import gi
import sports_planner_lib.athlete
import sports_planner_lib.db.schemas

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GtkCal", "0.1")
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk, GtkCal

from sports_planner.gui.about import show_about

logger = logging.getLogger(__name__)


class INSTALL_TYPE(enum.Enum):
    GLOBAL = enum.auto()
    LOCAL = enum.auto()
    WHEEL = enum.auto()


class Context(GObject.GObject):
    athlete: sports_planner_lib.athlete.Athlete
    _activity: sports_planner_lib.db.schemas.Activity | None = None
    install_type: INSTALL_TYPE | None = None

    @property
    def activity(self) -> sports_planner_lib.db.schemas.Activity | None:
        return self._activity

    @activity.setter
    def activity(self, activity):
        self._activity = self.athlete.get_activity_full(activity)
        self.emit("activity-changed")

    @GObject.Signal(name="activity-changed")
    def activity_changed(self):
        logger.debug(f"context activity changed to {self.activity}")


class SportsPlannerApplication(Adw.Application):
    def __init__(self, install_type=None, **kwargs):
        super().__init__(application_id="io.github.slaclau.sports-planner", **kwargs)
        self.install_type = install_type

    def do_startup(self):
        Adw.Application.do_startup(self)
        assert GtkCal.init()
        self._add_standard_actions()

    def do_activate(self):
        self.set_accels_for_action("win.show-help", ["F1"])

        win = self.props.active_window
        context = Context()
        context.athlete = self.get_athlete()
        context.install_type = self.install_type

        if not win:
            from sports_planner.gui.window import SportsPlannerWindow

            win = SportsPlannerWindow(application=self, context=context)

        win.present()

    def get_athlete(self):
        return sports_planner_lib.athlete.Athlete("seb.laclau@gmail.com")

    def _add_standard_actions(self):
        action = Gio.SimpleAction.new("show-about", None)
        action.connect(
            "activate",
            lambda action, _: show_about(
                self.get_application_id(),
                version("sports-planner"),
                self.props.active_window,
            ),
        )
        self.add_action(action)
