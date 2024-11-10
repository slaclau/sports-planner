import typing

import gi
import numpy as np
import pandas as pd
import plotly.express as px  # type: ignore
import plotly.graph_objects as go  # type: ignore
import plotly.io as pio  # type: ignore
import sweat  # type: ignore

from sports_planner.gui.activities.chart import (
    ActivityPlot,
    CurveViewer,
    HistogramViewer,
    MapViewer,
)
from sports_planner.gui.activities.overview import OverviewPage
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
        header = Adw.HeaderBar(
            show_end_title_buttons=False, show_start_title_buttons=False
        )
        self.activity_view.add_top_bar(header)
        settings_button = Gtk.Button(icon_name="open-menu-symbolic")
        settings_button.connect("clicked", self.open_settings)
        header.pack_end(settings_button)
        self.append(self.activity_view)
        self.switcher: typing.Optional[Gtk.StackSwitcher] = None
        self.stack: typing.Optional[Gtk.Stack] = None
        self.add_content()

    def spec_changed(self, source, data):
        self.emit("spec-changed", self)

    def add_content(self):
        self.stack = Gtk.Stack()
        if self.switcher is not None:
            self.activity_view.remove(self.switcher)
        switcher = Gtk.StackSwitcher(stack=self.stack)
        self.switcher = Gtk.ScrolledWindow()
        self.switcher.set_child(switcher)
        self.activity_view.add_top_bar(self.switcher)
        self.activity_view.set_content(self.stack)

        activity = self.activity

        records_df = activity.records_df

        for item in self.spec:
            name = self.spec[item]["name"]
            item_type = self.spec[item]["type"]
            page = self.get_page_for_spec(item_type, self.spec[item]["widget"])
            if page is None or page.get_first_child() is None:
                page = None
            if page is not None:
                self.stack.add_titled(page, item, name)

                page.connect("spec-changed", self.spec_changed)

    def get_page_for_spec(self, item_type: str, spec: Spec) -> Widget:
        if item_type == "overview":
            return OverviewPage(spec, self.activity)
        elif item_type == "map":
            return MapViewer(spec, self.activity)
        elif item_type == "activity_plot":
            return ActivityPlot(spec, self.activity)
        elif item_type == "activity_plot-gtk":
            return ActivityPlot(spec, self.activity, gtk=True)
        elif item_type == "df_viewer":
            return PandasViewer(spec, self.activity)
        elif item_type == "curve":
            return CurveViewer(spec, self.activity)
        elif item_type == "curve-gtk":
            return CurveViewer(spec, self.activity, gtk=True)
        elif item_type == "histogram":
            return HistogramViewer(spec, self.activity)
        elif item_type == "histogram-gtk":
            return HistogramViewer(spec, self.activity, gtk=True)


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
