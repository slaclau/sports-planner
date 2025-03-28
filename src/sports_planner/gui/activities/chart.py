import datetime
import logging
import time
from typing import TYPE_CHECKING

import gi
import numpy as np
import plotly.express as px  # type: ignore
import plotly.graph_objects as go  # type: ignore
import plotly.io as pio  # type: ignore
import sweat  # type: ignore
from plotly_gtk.chart import PlotlyGtk
from plotly_gtk.utils import get_base_fig
from plotly_gtk.webview import FigureWebView
from sports_planner_lib.db.schemas import Activity
from sports_planner_lib.metrics.pdm import Curve, DurationRegressor

from sports_planner.utils.logging import log_debug_time

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, Gio, Gtk

if TYPE_CHECKING:
    from sports_planner.gui.app import Context


logger = logging.getLogger(__name__)


class MapViewer(Gtk.Box):
    def __init__(self, name, context: "Context"):
        super().__init__()
        self.settings = Gio.Settings(
            schema_id="io.github.slaclau.sports-planner.views.activities.tabs.map",
            path=f"/io/github/slaclau/sports-planner/views/activities/tabs/{name}/",
        )
        self.settings.connect("changed", lambda s, k: self.add_content())
        self.context = context
        self.context.connect("activity-changed", lambda context: self.add_content())
        self.add_content()

    def add_content(self) -> None:
        if self.get_first_child():
            self.remove(self.get_first_child())
        zoom = self.settings.get_int("zoom")
        mapbox_style = self.settings.get_string("mapbox-style")
        # fig = get_base_fig()
        # fig["data"].append(
        #     dict(
        #         type="scattermapbox",
        #         lat=self.activity.records_df["latitude"],
        #         lon=self.activity.records_df["longitude"],
        #         mode="lines",
        #     )
        # )
        # fig["layout"]["mapbox"] = dict(
        #     style=mapbox_style,
        #     zoom=zoom,
        #     center=dict(
        #         lat=self.activity.records_df["latitude"].mean(),
        #         lon=self.activity.records_df["longitude"].mean(),
        #     ),
        # )
        activity = self.context.activity

        if "latitude" in activity.records_df and "longitude" in activity.records_df:
            fig = px.line_mapbox(
                activity.records_df,
                lat="latitude",
                lon="longitude",
                mapbox_style=mapbox_style,
                zoom=zoom,
            )
        else:
            fig = go.Figure()
        fig.layout.margin = dict(b=0, l=0, r=0, t=0)
        webview = FigureWebView(fig)
        webview.set_vexpand(True)
        webview.set_hexpand(True)
        self.append(webview)


class ActivityPlot(Gtk.Box):
    def __init__(self, name, context: "Context", gtk=False):
        super().__init__()
        self.gtk = gtk

        self.settings = Gio.Settings(
            schema_id="io.github.slaclau.sports-planner.views.activities.tabs.activity-plot",
            path=f"/io/github/slaclau/sports-planner/views/activities/tabs/{name}/",
        )
        self.settings.connect("changed", lambda s, k: self.add_content())
        self.context = context
        self.context.connect("activity-changed", lambda context: self.add_content())
        self.add_content()

    def add_content(self) -> None:
        gtk = self.gtk

        if self.get_first_child():
            self.remove(self.get_first_child())
        columns = self.settings.get_value("columns").unpack()

        activity = self.context.activity

        df = activity.records_df
        columns = [col for col in columns if col in df]
        fig = get_base_fig()
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

        if gtk:
            chart = PlotlyGtk(fig)
            chart.set_vexpand(True)
            chart.set_hexpand(True)
            self.append(chart)
        else:
            webview = FigureWebView(fig)
            webview.set_vexpand(True)
            webview.set_hexpand(True)
            self.append(webview)


class HistogramViewer(Gtk.Box):
    def __init__(self, activity: Activity, gtk=False):
        super().__init__(spec)
        self.activity = activity
        self.add_content(gtk)

    def add_content(self, gtk) -> None:
        column = self.spec["column"]
        if column not in self.activity.records_df.columns:
            return None

        fig = get_base_fig()

        fig["data"].append(dict(x=self.activity.records_df[column], type="histogram"))
        if gtk:
            chart = PlotlyGtk(fig)
            chart.set_vexpand(True)
            chart.set_hexpand(True)
            self.append(chart)
        else:
            webview = FigureWebView(fig)
            webview.set_vexpand(True)
            webview.set_hexpand(True)
            self.append(webview)


class CurveViewer(Adw.Bin):
    def __init__(self, name, context: "Context", gtk=True):
        super().__init__()
        self.gtk = gtk

        self.settings = Gio.Settings(
            schema_id="io.github.slaclau.sports-planner.views.activities.tabs.curve",
            path=f"/io/github/slaclau/sports-planner/views/activities/tabs/{name}/",
        )
        self.settings.connect("changed", lambda s, k: self.add_content())
        self.context = context
        self.context.connect("activity-changed", lambda context: self.add_content())
        self.add_content()

    def add_content(self) -> None:
        period = {"days": 42}
        configured_model = "3 param"

        gtk = self.gtk

        column = self.settings.get_string("column")
        activity = self.context.activity

        curve = activity.get_metric(Curve[column])
        df = activity.meanmaxes_df

        if curve is None or f"mean_max_{column}" not in df:
            self.set_child(None)
            return
        y = df[f"mean_max_{column}"]

        date = activity.timestamp.date()
        t = time.time()
        historical = self.context.athlete.get_mean_max_for_period(
            column,
            activity.get_metric("Sport")["sport"],
            date - datetime.timedelta(**period),
            date + datetime.timedelta(days=1),
        )
        t = log_debug_time(t, "get hist")
        bests = self.context.athlete.get_bests_for_period(
            column,
            activity.get_metric("Sport")["sport"],
            date - datetime.timedelta(**period),
            date + datetime.timedelta(days=1),
        )
        t = log_debug_time(t, "get bests")

        x = list(range(1, len(y) + 1))
        X = sweat.array_1d_to_2d(x)

        regressor = DurationRegressor(model=configured_model)
        regressor.fit(
            sweat.array_1d_to_2d(bests[bests.duration < 1200].duration),
            bests[bests.duration < 1200][f"mean_max_{column}"],
        )
        predicted = regressor.predict(X)
        t = log_debug_time(t, "fit and predict")

        params = regressor.get_fitted_params()
        logger.debug(f"fit {configured_model} with params {params}")

        fig = get_base_fig()

        fig["data"].append(dict(x=x, y=y, name="Actual", mode="lines", type="scatter"))
        fig["data"].append(
            dict(
                x=historical.duration,
                y=historical[f"mean_max_{column}"],
                name="Historical",
                mode="lines",
                type="scatter",
                visible="legendonly",
            )
        )
        fig["data"].append(
            dict(
                x=bests.duration,
                y=bests[f"mean_max_{column}"],
                name="Bests",
                mode="markers",
                type="scatter",
            )
        )
        fig["data"].append(
            dict(
                x=x,
                y=predicted,
                name="Predicted",
                mode="lines",
                type="scatter",
            )
        )
        param_map = {"cp": "Critical Power", "w_prime": "W'", "p_max": "Maximum Power"}
        param_units = {"cp": "W", "w_prime": "kJ", "p_max": "W"}
        power_formatter = lambda p: f"{p:0.0f}"
        param_formatters = {
            "cp": power_formatter,
            "w_prime": lambda w: f"{w/1000:0.1f}",
            "p_max": power_formatter,
        }
        fig["layout"]["annotations"] = [
            dict(
                x=0,
                y=1,
                align="left",
                showarrow=False,
                xanchor="left",
                yanchor="bottom",
                xref="paper",
                yref="paper",
                text="<br>".join(
                    [
                        f"{param_map[param]}: {param_formatters[param](value)} {param_units[param]}"
                        for param, value in params.items()
                    ]
                ),
            )
        ]

        ticks = np.array(
            [
                1,
                15,
                60,
                300,
                600,
                1200,
                1800,
                2700,
                3600,
                5400,
                3600 * 2,
                3600 * 3,
                3600 * 4,
                3600 * 5,
                3600 * 6,
                3600 * 8,
                3600 * 12,
                3600 * 18,
            ]
        )

        ticklabels = []
        for tick in ticks:
            hours = int(np.floor(tick / 3600))
            tick = tick - 3600 * hours
            mins = int(np.floor(tick / 60))
            secs = int(tick - 60 * mins)
            ticklabel = ""
            if hours > 0:
                ticklabel += f"{hours:d}h"
            if mins > 0:
                ticklabel += f"{mins:d}m"
            if secs > 0:
                ticklabel += f"{secs:d}s"

            ticklabels.append(ticklabel)

        fig["layout"].update(
            dict(
                xaxis=dict(
                    tickmode="array",
                    tickvals=ticks,
                    ticktext=ticklabels,
                    rangemode="tozero",
                    type="log",
                ),
                yaxis_title_text=column,
            )
        )

        if gtk:
            chart = PlotlyGtk(fig)
            chart.set_vexpand(True)
            chart.set_hexpand(True)
            self.set_child(chart)
        else:
            webview = FigureWebView(fig)
            webview.set_vexpand(True)
            webview.set_hexpand(True)
            self.set_child(webview)
