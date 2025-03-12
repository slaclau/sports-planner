from numbers import Number
from typing import TYPE_CHECKING
import logging

import numpy as np

import gi

import sports_planner.utils.format

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, Gio, GObject

from sports_planner_lib.metrics.calculate import parse_metric_string, get_all_metrics
from sports_planner_lib.metrics.base import Metric

if TYPE_CHECKING:
    from sports_planner.gui.app import Context

logger = logging.getLogger(__name__)


class Metric(Gtk.Label):
    metric_class: type(Metric)
    fields: list[str]

    def __init__(self, config_path: str, context: "Context"):
        super().__init__()
        self.add_css_class("title-1")
        self.add_css_class("accent")
        self.context = context
        self.settings = Gio.Settings(
            schema_id=f"io.github.slaclau.sports-planner.views.activities.tabs.overview.tile.metric",
            path=config_path,
        )
        self.settings.connect("changed::metric", lambda s, k: self._update())
        self.context.connect("activity-changed", lambda _: self._update())
        self._update()

    def _update(self):
        logger.debug("updating")

        logger.debug("adding metric")
        metric = self.settings.get_string("metric")

        value = self.context.activity.get_metric(metric)
        self.metric_class, self.fields = parse_metric_string(metric)
        if self.metric_class is None:
            logger.error(f"Unknown metric {metric}")

        if value is None or isinstance(value, Number) and np.isnan(value):
            return

        logger.debug(f"adding {self.metric_class.name} [{self.fields}]: {value}")
        unit = self.metric_class.unit

        if unit == "s":
            value = sports_planner.utils.format.time(value)
            unit = ""
        else:
            value = f"{value:{self.metric_class.format}}"

        self.set_text(f"{value}{f" {unit}" if unit else ""}")

    def get_settings_pages(self):
        metrics_page = Adw.PreferencesPage(title="Metric", icon_name="cycling-symbolic")
        metrics_group = Adw.PreferencesGroup(title="Metric")
        metrics_page.add(metrics_group)

        return [metrics_page]
