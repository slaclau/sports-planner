import gi
import numpy as np
import pandas as pd
import plotly.express as px  # type: ignore
import plotly.graph_objects as go  # type: ignore
import plotly.io as pio  # type: ignore
import sweat  # type: ignore

from sports_planner.gui.activities.chart import ActivityPlot, MapViewer
from sports_planner.gui.activities.overview import OverviewPage
from sports_planner.gui.chart import FigureWebView
from sports_planner.gui.widgets.base import Spec, Widget
from sports_planner.io.files import Activity

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("WebKit", "6.0")
from gi.repository import Adw, Gtk  # noqa: E402


class ActivityView(Widget):
    def __init__(self, activity: Activity, spec: dict[str, Spec]) -> None:
        super().__init__(spec)
        self.activity = activity
        self.activity_view = Adw.ToolbarView(hexpand=True, vexpand=True)
        self.append(self.activity_view)

        self.add_content()

    def spec_changed(self, source, data):
        self.emit("spec-changed", self)

    def add_content(self):
        stack = Gtk.Stack()
        header = Gtk.StackSwitcher(stack=stack)
        self.activity_view.add_top_bar(header)
        self.activity_view.set_content(stack)

        activity = self.activity

        records_df = activity.records_df

        for item in self.spec:
            name = self.spec[item]["name"]
            item_type = self.spec[item]["type"]
            page = self.get_page_for_spec(item_type, self.spec[item]["widget"])
            if page is not None:
                stack.add_titled(page, item, name)
                page.connect("spec-changed", self.spec_changed)

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

    def get_page_for_spec(self, item_type: str, spec: Spec) -> Widget:
        if item_type == "overview":
            return OverviewPage(spec, self.activity)
        elif item_type == "map":
            return MapViewer(spec, self.activity)
        elif item_type == "activity_plot":
            return ActivityPlot(spec, self.activity)
        elif item_type == "df_viewer":
            return PandasViewer(spec, self.activity)

    @staticmethod
    def create_powercurve(df: pd.DataFrame, column: str) -> FigureWebView:
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


class PandasViewer(Widget):
    def __init__(self, spec: dict[str, Spec], activity: Activity) -> None:
        super().__init__(spec)
        self.activity = activity
        self.add_content()

    def add_content(self) -> None:
        dataframe_type = self.spec["type"]
        if dataframe_type == "records":
            df = self.activity.records_df
        elif dataframe_type == "hrv":
            df = self.activity.hrv_df
        elif dataframe_type == "laps":
            df = self.activity.laps_df
        elif dataframe_type == "sessions":
            df = self.activity.sessions_df
        if not isinstance(df, pd.DataFrame) or len(df.index) == 0:
            return None
        try:
            df = df.sweat.to_timedelta_index()
            df.insert(0, "time", df.index)
            if hasattr(df.index, "seconds"):
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
        types: list[type] = [int]

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
            tree_column = Gtk.TreeViewColumn(column_title, renderer, text=i)  # type: ignore
            tree_column.set_sort_column_id(i)
            tree_column.set_reorderable(True)
            view.append_column(tree_column)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroller.set_child(view)
        scroller.set_vexpand(True)
        scroller.set_hexpand(True)
        self.append(scroller)
