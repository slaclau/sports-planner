from numbers import Number
from typing import TYPE_CHECKING
import logging

import numpy as np

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, Gio, GObject

from sports_planner_lib.metrics.calculate import parse_metric_string, get_all_metrics
from sports_planner_lib.metrics.base import Metric

if TYPE_CHECKING:
    from sports_planner.gui.app import Context

logger = logging.getLogger(__name__)


class Metric(Gtk.Box):
    metric_class: type(Metric)
    fields: list[str]

    def __init__(self, config_path: str, context: "Context"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.context = context
        self.settings = Gio.Settings(
            schema_id=f"io.github.slaclau.sports-planner.views.activities.tabs.overview.tile.metric",
            path=config_path,
        )
        self.tile_settings = Gio.Settings(
            schema_id=f"io.github.slaclau.sports-planner.views.activities.tabs.overview.tile",
            path=config_path,
        )
        self.settings.connect("changed::metric", lambda s, k: self._update())
        self.tile_settings.connect("changed::height", lambda s, k: self._update())
        self.context.connect("activity-changed", lambda _: self._update())

        self.title_class = ""

        self.value_label = Gtk.Label()
        self.value_label.add_css_class("accent")

        self.unit_label = Gtk.Label()

        self.append(self.value_label)
        self.append(self.unit_label)
        self._update()

    def _update(self):
        logger.debug("updating")
        if self.title_class != "":
            self.value_label.remove_css_class(self.title_class)
        height = self.tile_settings.get_int("height")
        if height >= 5:
            self.title_class = "title-1"
        else:
            self.title_class = "title-2"
        if height >= 6:
            self.unit_label.set_visible(True)
        else:
            self.unit_label.set_visible(False)
        self.value_label.add_css_class(self.title_class)

        logger.debug("adding metric")
        metric = self.settings.get_string("metric")

        value = self.context.activity.get_metric(metric)
        self.metric_class, self.fields = parse_metric_string(metric)
        if self.metric_class is None:
            logger.error(f"Unknown metric {metric}")

        if value is None or isinstance(value, Number) and np.isnan(value):
            return

        logger.debug(f"adding {self.metric_class.name} [{self.fields}]: {value}")
        _, value, unit = self.metric_class.format(value)

        self.value_label.set_text(value)
        self.unit_label.set_text(unit)

    def get_settings_pages(self):
        metrics_page = Adw.PreferencesPage(title="Metric", icon_name="cycling-symbolic")
        metrics_group = Adw.PreferencesGroup(title="Metric")
        metrics_page.add(metrics_group)

        metrics = get_all_metrics()
        metrics_map = {
            metric.name: metric for metric in metrics if hasattr(metric, "name")
        }
        metrics_strings = sorted(metrics_map.keys())
        metrics_list = Gtk.StringList(strings=metrics_strings)
        metric_row = Adw.ComboRow(title="Metric")
        metric_row.set_model(metrics_list)
        current = self.settings.get_string("metric")
        current, _ = parse_metric_string(current)

        print(metrics_strings)

        metrics_group.add(metric_row)
        if current is not None:
            idx = metrics_strings.index(current.name)
            metric_row.set_selected(idx)

        metric_row.connect(
            "notify::selected",
            lambda row, _: self.settings.set_string(
                "metric",
                metrics_map[row.get_selected_item().get_string()].__name__,
            ),
        )

        return [metrics_page]
