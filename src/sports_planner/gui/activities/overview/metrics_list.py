from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio

from sports_planner_lib.metrics.calculate import get_metric

if TYPE_CHECKING:
    from sports_planner.gui.app import Context


class MetricsList(Gtk.Grid):
    def __init__(self, config_path: str, tile_type: str, context: "Context"):
        super().__init__()
        self.settings = Gio.Settings(
            schema_id=f"io.github.slaclau.sports-planner.views.activities.tabs.overview.tile.{tile_type}",
            path=config_path,
        )
        metrics = self.settings.get_value("metrics").unpack()
        for i in range(0, len(metrics)):
            metric = metrics[i]
            value = context.activity.get_metric(metric)
            metric_class = get_metric(metric)

            self.attach(Gtk.Label(label=f"{metric_class.name}:"), 0, i, 1, 1)
            self.attach(
                Gtk.Label(label=f"{value:{metric_class.format}}", xalign=1), 1, i, 1, 1
            )
            self.attach(Gtk.Label(label=metric_class.unit), 2, i, 1, 1)
