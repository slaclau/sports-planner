from numbers import Number
from typing import TYPE_CHECKING
import logging

import numpy as np

import gi

import sports_planner.utils.format

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, Gio

from sports_planner_lib.metrics.calculate import get_metric, parse_metric_string

if TYPE_CHECKING:
    from sports_planner.gui.app import Context

logger = logging.getLogger(__name__)


class MetricsList(Gtk.Grid):
    def __init__(self, config_path: str, context: "Context"):
        super().__init__(margin_start=5, margin_end=5, column_homogeneous=False)
        self.context = context
        self.settings = Gio.Settings(
            schema_id=f"io.github.slaclau.sports-planner.views.activities.tabs.overview.tile.metrics-list",
            path=config_path,
        )
        self.settings.connect("changed::metrics", lambda s, k: self._update())
        self.context.connect("activity-changed", lambda context: self._update())
        self._update()

    def _update(self):
        logger.debug("updating")
        child = self.get_first_child()
        while child is not None:
            next = child.get_next_sibling()
            self.remove(child)
            child = next

        logger.debug("adding metrics")
        metrics = self.settings.get_value("metrics").unpack()
        for i in range(0, len(metrics)):
            metric = metrics[i]

            value = self.context.activity.get_metric(metric)
            metric_class, fields = parse_metric_string(metric)
            if metric_class is None:
                logger.error(f"Unknown metric {metric}")

            if value is None or isinstance(value, Number) and np.isnan(value):
                continue

            logger.debug(f"adding {metric_class.name} [{fields}]: {value}")
            unit = metric_class.unit

            if unit == "s":
                value = sports_planner.utils.format.time(value)
                unit = ""
            else:
                value = f"{value:{metric_class.format}}"

            if len(fields) == 0:
                self.attach(
                    Gtk.Label(label=f"{metric_class.name}: ", xalign=0), 0, i, 1, 1
                )
            else:
                self.attach(
                    Gtk.Label(
                        label=f"{metric_class.name} [{", ".join(fields)}]: ", xalign=0
                    ),
                    0,
                    i,
                    1,
                    1,
                )
            self.attach(Gtk.Label(label=f"{value} ", xalign=1), 1, i, 1, 1)
            self.attach(Gtk.Label(label=unit, xalign=0), 2, i, 1, 1)

    def get_settings_pages(self):
        metrics_page = Adw.PreferencesPage(
            title="Metrics", icon_name="cycling-symbolic"
        )
        metrics_group = Adw.PreferencesGroup(title="Metrics")
        metrics_page.add(metrics_group)

        for metric in self.settings.get_value("metrics").unpack():
            metrics_group.add(Adw.ActionRow(title=parse_metric_string(metric)[0].name))

        metrics_group.add(Adw.ActionRow(icon_name="plus-symbolic"))

        return [metrics_page]
