from typing import TYPE_CHECKING

import gi
import numpy as np
import plotly.express as px  # type: ignore
import plotly.graph_objects as go  # type: ignore
import plotly.io as pio  # type: ignore
import sports_planner_lib.db.schemas
import sweat  # type: ignore
from plotly_gtk.chart import PlotlyGtk
from plotly_gtk.utils import get_base_fig
from plotly_gtk.webview import FigureWebView
from sports_planner_lib.db.schemas import Activity
from sports_planner_lib.metrics.pdm import Curve

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, Gtk

if TYPE_CHECKING:
    from sports_planner.gui.main import Context


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
        activity = self.context.athlete.get_activity_full(
            self.context.activity,
        )
        fig = px.line_mapbox(
            activity.records_df,
            lat="latitude",
            lon="longitude",
            mapbox_style=mapbox_style,
            zoom=zoom,
        )
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

        activity = self.context.athlete.get_activity_full(
            self.context.activity,
        )
        df = activity.records_df
        columns = set(df.columns).intersection(columns)
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


class CurveViewer:
    def __init__(self, activity: Activity, gtk=False):
        super().__init__(spec)
        self.activity = activity
        self.add_content(gtk)

    def add_content(self, gtk) -> None:
        column = self.spec["column"]
        curve = self.activity.get_metric(Curve[column])
        if curve is None:
            return None
        x = curve["x"]
        y = curve["y"]
        data = curve["predictions"]

        fig = get_base_fig()

        fig["data"].append(dict(x=x, y=y, name="Actual", mode="lines", type="scatter"))
        all_button = {
            "label": "All",
            "method": "update",
            "args": [
                {
                    "visible": np.tile([True], 1 + len(data.columns)),
                    "title": "All models",
                    "showlegend": True,
                }
            ],
        }

        buttons = [all_button]

        default = "3 param" if "3 param" in data.columns else "omni"

        for model in data.columns:
            fig["data"].append(
                dict(
                    x=x,
                    y=data[model],
                    name=model,
                    mode="lines",
                    visible=(model == default),
                    type="scatter",
                )
            )
            button = {
                "label": model,
                "method": "update",
                "args": [
                    {
                        "visible": np.concatenate([[True], data.columns.isin([model])]),
                        "title": model,
                        "showlegend": True,
                    }
                ],
            }
            buttons.append(button)

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
                updatemenus=[
                    {
                        "active": list(data.columns).index(default) + 1,
                        "buttons": buttons,
                    }
                ],
            )
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
