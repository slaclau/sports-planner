import os
from tempfile import NamedTemporaryFile

import gi
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import sweat

from time import time
from sports_planner.utils.logging import logtime

from sports_planner.io.files import read_file, Activity

from sports_planner.gui.chart import FigureWebView

from sports_planner.metrics.calculate import MetricsCalculator
from sports_planner.metrics.govss import GOVSS
from sports_planner.metrics.coggan import CogganTSS, CogganVI

pio.templates.default = "plotly"

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("WebKit", "6.0")
from gi.repository import Gtk, Adw, WebKit  # noqa: E402


class ActivityView:
    @staticmethod
    def create(activity: Activity):
        activity_view = Adw.ToolbarView()
        stack = Gtk.Stack()
        header = Gtk.StackSwitcher(stack=stack)
        activity_view.add_top_bar(header)
        activity_view.set_content(stack)

        records_df = activity.records_df
        laps_df = activity.laps_df
        sessions_df = activity.sessions_df
        hrv_df = activity.hrv_df

        stack.add_titled(
            ActivityView.create_activity_plot(records_df),
            "activity_chart",
            "Activity Chart",
        )
        stack.add_titled(
            ActivityView.create_pandas_viewer(records_df), "records", "Records"
        )
        if len(hrv_df.index) > 0:
            stack.add_titled(ActivityView.create_pandas_viewer(hrv_df), "hrv", "HRV")
        stack.add_titled(ActivityView.create_pandas_viewer(laps_df), "laps", "Laps")
        stack.add_titled(
            ActivityView.create_pandas_viewer(sessions_df),
            "sessions",
            "Sessions",
        )
        if "latitude" in records_df.columns and "longitude" in records_df.columns:
            stack.add_titled(ActivityView.create_map_viewer(records_df), "map", "Map")
        try:
            stack.add_titled(
                ActivityView.create_powercurve(records_df, "speed"),
                "speed_curve",
                "Speed curve",
            )
        except KeyError:
            pass
        except ValueError:
            pass
        except RuntimeError:
            pass
        try:
            stack.add_titled(
                ActivityView.create_powercurve(records_df, "power"),
                "power_curve",
                "Power curve",
            )
        except KeyError:
            pass
        except ValueError:
            pass
        except RuntimeError:
            pass

        return activity_view

    @staticmethod
    def create_pandas_viewer(df: pd.DataFrame):
        start = time()
        try:
            df = df.sweat.to_timedelta_index()
            df.insert(0, "time", df.index)
            df.index = df.index.seconds
        except AttributeError:
            pass
        except IndexError:
            pass

        dtypes = list(df.dtypes)
        types_map = {
            np.dtype("float64"): float,
            np.dtype("int64"): int,
        }
        types = [int]

        for dtype, column in zip(dtypes, df.columns):
            if dtype in types_map:
                types.append(types_map[dtype])
            else:
                df[column] = df[column].astype(str)
                types.append(str)
        store = Gtk.ListStore(*types)

        for row in df.itertuples():
            store.append(list(row))

        view = Gtk.TreeView(model=store)
        for i, column_title in enumerate(df.columns, start=1):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            column.set_sort_column_id(i)
            column.set_reorderable(True)
            view.append_column(column)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroller.set_child(view)
        clamp = Adw.Clamp()
        clamp.set_child(scroller)

        logtime(start, "DataFrame viewer took")
        return scroller

    @staticmethod
    def create_summary_page(df: pd.DataFrame):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        for column in df.columns:
            inner_box = Gtk.Box()
            inner_box.append(Gtk.Label(label=column))
            inner_box.append(Gtk.Entry(text=df.iloc[0][column], editable=False))
            box.append(inner_box)

        return box

    @staticmethod
    def create_map_viewer(df: pd.DataFrame):
        fig = px.line_mapbox(
            df, lat="latitude", lon="longitude", mapbox_style="open-street-map", zoom=13
        )
        return FigureWebView(fig)

    @staticmethod
    def create_activity_plot(df: pd.DataFrame, type=None):
        fig = go.Figure()
        i = 0
        standard_columns = {
            "speed",
            "cadence",
            "power",
            "heartrate",
            "performance_condition",
            "altitude",
        }
        exclude_columns = {
            "timestamp",
            "latitude",
            "longitude",
            "lap",
            "position_lat",
            "position_long",
            "altitude",
            "distance",
            "record_sequence",
            "session",
            "unknown_87",
            "unknown_88",
        }
        cycling_dynamics = {
            "left_right_balance",
            "left_torque_effectiveness",
            "right_torque_effectiveness",
            "left_pedal_smoothness",
            "right_pedal_smoothness",
            "left_pco",
            "right_pco",
            "left_power_phase",
            "left_power_phase_peak",
            "right_power_phase",
            "right_power_phase_peak",
            "bal",
        }

        if type == "cycling_dynamics":
            columns = set(df.columns).intersection(cycling_dynamics)
        else:
            columns = set(df.columns).intersection(standard_columns)
        for column in columns:
            i += 1
            if i == 1:
                fig.add_trace(
                    go.Scatter(x=df.index, y=df[column], name=column, mode="lines")
                )
                fig.update_layout(**{f"yaxis": dict(title=column)})
            else:
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=df[column],
                        yaxis=f"y{i}",
                        name=column,
                        mode="lines",
                    )
                )
                fig.update_layout(
                    **{
                        f"yaxis{i}": dict(
                            overlaying="y",
                            side="left",
                            autoshift=True,
                            anchor="free",
                            title=column,
                        )
                    }
                )

        return FigureWebView(fig)

    @staticmethod
    def create_powercurve(df: pd.DataFrame, column):
        pc_df = df.sweat.mean_max(column, monotonic=True)
        x = pc_df.index.total_seconds()
        X = sweat.array_1d_to_2d(x)
        y = pc_df["mean_max_" + column]

        two_param = sweat.PowerDurationRegressor(model="2 param")
        two_param.fit(X, y)

        three_param = sweat.PowerDurationRegressor(model="3 param")
        three_param.fit(X, y)

        exponential = sweat.PowerDurationRegressor(model="exponential")
        exponential.fit(X, y)

        omni = sweat.PowerDurationRegressor(model="omni")
        omni.fit(X, y)

        data = pd.DataFrame(
            {
                "2 param": two_param.predict(X),
                "3 param": three_param.predict(X),
                "exponential": exponential.predict(X),
                "omni": omni.predict(X),
            }
        )

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                name="Actual",
                mode="lines",
            )
        )
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

        default = "3 param"

        for model in data.columns:
            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=data[model],
                    name=model,
                    mode="lines",
                    visible=(model == default),
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

        fig.update_layout(
            xaxis=dict(
                tickmode="array",
                tickvals=ticks,
                ticktext=ticklabels,
                rangemode="tozero",
                type="log",
            ),
            yaxis_title=column,
            updatemenus=[
                {"active": list(data.columns).index(default) + 1, "buttons": buttons}
            ],
        )
        fig.update()

        return FigureWebView(fig)
