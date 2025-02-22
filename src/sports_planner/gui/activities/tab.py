import logging

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, GObject, Gtk


from sports_planner.gui.activities import chart
from sports_planner.gui.activities.overview.overview import Overview

logger = logging.getLogger(__name__)


class ActivityTab(Adw.Bin):
    def __init__(self, name="", context=None, **kwargs):
        super().__init__(**kwargs)

        self.name = name
        self.context = context

        self.settings = Gio.Settings(
            schema_id="io.github.slaclau.sports-planner.views.activities.tab",
            path=f"/io/github/slaclau/sports-planner/views/activities/tabs/{name}/",
        )
        self.title = self.settings.get_string("title")

        self.set_content()
        self.settings.connect("changed::type", lambda s, k: self.set_content())

        logger.debug(f"Adding tab name {name}, title {self.title}")

    def set_content(self):
        tab_type = self.settings.get_string("type")

        if "gtk" in tab_type:
            tab_type = tab_type.replace("-gtk", "")
            gtk = True
        else:
            gtk = False

        if tab_type == "overview":
            self.set_child(Overview(self.name, self.context))
        elif tab_type == "map":
            self.set_child(chart.MapViewer(self.name, self.context))
        elif tab_type == "activity-plot":
            self.set_child(chart.ActivityPlot(self.name, self.context, gtk=gtk))
