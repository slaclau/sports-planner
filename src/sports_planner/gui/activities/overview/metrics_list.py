from numbers import Number
from typing import TYPE_CHECKING
import logging

import numpy as np

import gi

import sports_planner.utils.format

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, Gio

from sports_planner_lib.metrics.calculate import parse_metric_string, get_all_metrics

if TYPE_CHECKING:
    from sports_planner.gui.app import Context

logger = logging.getLogger(__name__)


class MetricsList(Gtk.Grid):
    def __init__(self, config_path: str, context: "Context"):
        super().__init__(margin_start=5, margin_end=5)
        self.context = context
        self.settings = Gio.Settings(
            schema_id=f"io.github.slaclau.sports-planner.tabs.overview.tile.metrics-list",
            path=config_path,
        )
        self.settings.connect("changed::metrics", lambda s, k: self._update())
        self.context.connect("activity-changed", lambda _: self._update())
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
            value = self.context.activity.get_metric(
                metric, athlete=self.context.athlete
            )
            metric_class, fields = parse_metric_string(metric)
            if metric_class is None:
                logger.error(f"Unknown metric {metric}")
            self.attach(Gtk.Label(label=f"{metric_class.name}: ", xalign=0), 0, i, 1, 1)

            if value is None or isinstance(value, Number) and np.isnan(value):
                continue

            logger.debug(f"adding {metric_class.name} [{fields}]: {value}")
            name, value, unit = metric_class.format(value)

            self.attach(Gtk.Label(label=f"{value} ", xalign=1), 1, i, 1, 1)
            self.attach(Gtk.Label(label=unit, xalign=0), 2, i, 1, 1)

    def get_settings_pages(self):
        metrics_page = Adw.PreferencesPage(
            title="Metrics", icon_name="cycling-symbolic"
        )
        metrics_group = Adw.PreferencesGroup(title="Metrics")
        metrics_page.add(metrics_group)

        metrics = get_all_metrics()
        metrics_map = {
            metric.name: metric for metric in metrics if hasattr(metric, "name")
        }
        metrics_strings = sorted(metrics_map.keys())
        metrics_list = Gtk.StringList(strings=metrics_strings)

        settings = self.settings.get_value("metrics").unpack()

        for i in range(0, len(settings)):
            metric = settings[i]
            metric, _ = parse_metric_string(metric)

            row = Adw.ComboRow()
            row.set_model(metrics_list)
            if metric is not None:
                row.set_selected(metrics_strings.index(metric.name))

            def update_settings(r):
                settings[i] = metrics_map[r.get_selected_item().get_string()].__name__
                self.settings.set_strv("metrics", settings)

            row.connect("notify::selected", lambda r, _: update_settings(r))
            metrics_group.add(row)

        more_row = Adw.ButtonRow(
            start_icon_name="plus-large-symbolic", title="Add metric"
        )

        def add_row():
            metrics_group.remove(more_row)
            settings.append("")

            row = Adw.ComboRow()
            row.set_model(metrics_list)

            def update_settings(r):
                settings[-1] = metrics_map[r.get_selected_item().get_string()].__name__
                self.settings.set_strv("metrics", settings)

            row.connect("notify::selected", lambda r, _: update_settings(r))
            metrics_group.add(row)
            metrics_group.add(more_row)

        more_row.connect("activated", lambda _: add_row())
        metrics_group.add(more_row)

        return [metrics_page]
