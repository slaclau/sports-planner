import importlib.resources
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk


@Gtk.Template(
    resource_path="/io/github/slaclau/sports-planner/gtk/activities/calendar.ui"
)
class Calendar(Gtk.Box):
    __gtype_name__ = "Calendar"
