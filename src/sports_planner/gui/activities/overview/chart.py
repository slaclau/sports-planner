from numbers import Number
from typing import TYPE_CHECKING
import logging

import numpy as np

import gi
from plotly_gtk.chart import PlotlyGtk
from plotly_gtk.utils import get_base_fig

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, Gio, GObject

from sports_planner_lib.metrics.calculate import parse_metric_string, get_all_metrics
from sports_planner_lib.metrics.base import Metric

if TYPE_CHECKING:
    from sports_planner.gui.app import Context

logger = logging.getLogger(__name__)


class Chart(Adw.Bin):
    def __init__(self, config_path: str, context: "Context"):
        super().__init__()
        self.context = context
        self.settings = Gio.Settings(
            schema_id=f"io.github.slaclau.sports-planner.tabs.overview.tile.chart",
            path=config_path,
        )
        self.settings.connect("changed::chart-columns", lambda s, k: self._update())
        self.context.connect("activity-changed", lambda _: self._update())

        self._update()

    def _update(self):
        columns = self.settings.get_value("chart-columns").unpack()

        activity = self.context.activity

        df = activity.records_df
        columns = [col for col in columns if col in df]
        fig = get_base_fig()
        fig["layout"]["margin"] = dict(l=20, r=20, t=20, b=20)
        i = 0
        for column in columns:
            i += 1
            if i == 1:
                fig["data"].append(
                    dict(
                        x=df.index,
                        y=df[column],
                        name=column,
                        mode="lines",
                        type="scatter",
                    )
                )
                fig["layout"][f"yaxis"] = dict(title=dict(text=column))
            else:
                fig["data"].append(
                    dict(
                        x=df.index,
                        y=df[column],
                        yaxis=f"y{i}",
                        name=column,
                        mode="lines",
                        type="scatter",
                    )
                )
                fig["layout"][f"yaxis{i}"] = dict(
                    overlaying="y",
                    side="left",
                    autoshift=True,
                    anchor="free",
                    title=dict(text=column),
                )

            chart = PlotlyGtk(fig)
            chart.set_vexpand(True)
            chart.set_hexpand(True)
            self.set_child(chart)
