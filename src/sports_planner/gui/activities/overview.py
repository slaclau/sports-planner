import datetime
import json
import tempfile

import gi
import plotly.express as px

from sports_planner.gui.chart import FigureWebView
from sports_planner.gui.widgets.base import Spec, Widget
from sports_planner.io.files import Activity
from sports_planner.metrics.calculate import get_metric

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")
from gi.repository import Adw, Gdk, Gio, GObject, Gtk, WebKit


class OverviewPage(Widget):
    def __init__(
        self,
        spec: Spec,
        activity: Activity | None = None,
    ):
        super().__init__(spec)
        self.activity = activity

        self.add_content()

    def get_frame_at(self, i: int, j: int) -> "DropFrame":
        child = self.grid.get_child_at(i, j)
        assert isinstance(child, DropFrame)
        return child

    def move(self, frame_to: "DropFrame", pos_from: tuple[int, int]) -> None:
        frame_from = self.get_frame_at(*pos_from)
        child = frame_from.get_child()
        frame_from.spec = None
        frame_from.add_content()
        frame_to.set_child(child)

    def add_content(self):  # type: ignore
        if self.spec["type"] == "grid":
            self.grid = Gtk.Grid(column_homogeneous=True, hexpand=True)
            self.append(self.grid)
            spec = self.spec["list"]
            longest_column = max([len(column) for column in spec])
            for i in range(0, len(spec)):
                column = spec[i]
                for j in range(0, longest_column + 1):
                    cell = column[j] if j < len(column) else None
                    frame = DropFrame(self, cell)
                    frame.connect("spec-changed", self.on_spec_changed)
                    self.grid.attach(frame, i, j, 1, 1)
        elif self.spec["type"] == "complex-grid":
            homogeneous = self.spec["homogeneous"]
            scroller = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
            self.grid = Gtk.Grid(column_homogeneous=homogeneous, hexpand=True)
            scroller.set_child(self.grid)
            self.append(scroller)
            spec = self.spec["list"]
            for item in spec:
                width = item["width"] if "width" in item else 1
                height = item["width"] if "height" in item else 1
                frame = DropFrame(self, item["widget"])
                frame.connect("spec-changed", self.on_spec_changed)
                self.grid.attach(frame, item["column"], item["row"], width, height)
        elif self.spec["type"] == "flex-grid":
            outer_box = Gtk.Box(hexpand=True, homogeneous=True)
            self.append(outer_box)
            for column in self.spec["list"]:
                box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                outer_box.append(box)
                for cell in column:
                    frame = DropFrame(self, cell)
                    frame.connect("spec-changed", self.on_spec_changed)
                    box.append(frame)
        elif self.spec["type"] == "flow":
            scroller = Gtk.ScrolledWindow(
                hscrollbar_policy=Gtk.PolicyType.NEVER,
                valign=Gtk.Align.FILL,
                vexpand=True,
            )
            scroller.set_size_request(0, -1)
            flow = Gtk.FlowBox(
                orientation=Gtk.Orientation.VERTICAL,
                valign=Gtk.Align.FILL,
                vexpand=True,
            )
            flow.set_size_request(0, -1)
            scroller.set_child(flow)
            self.append(scroller)
            for item in self.spec["list"]:
                frame = DropFrame(self, item)
                frame.connect("spec-changed", self.on_spec_changed)
                flow.append(frame)

    def on_spec_changed(self, source, data):
        if self.spec["type"] == "grid":
            pos = self.grid.query_child(source)
            self.spec["list"][pos[0]][pos[1]] = data.spec
            self.emit("spec-changed", self)
        elif self.spec["type"] == "complex-grid":
            pos = self.grid.query_child(source)
            for item in self.spec["list"]:
                if item["column"] == pos[0] and item["row"] == pos[1]:
                    item["widget"] = data.spec
                    break
            self.emit("spec-changed", self)


class DropFrame(Widget):
    def __init__(
        self, overview: OverviewPage, spec: dict | None, draggable=False
    ) -> None:
        super().__init__(spec)
        self.draggable = draggable
        self.overview = overview
        self.frame = Gtk.Frame()
        self.append(self.frame)

        if draggable:
            dest = Gtk.DropTarget.new(str, Gdk.DragAction.MOVE)
            dest.connect("drop", self.on_drop)
            self.add_controller(dest)
            self.controller = dest

        self.add_content()
        self.occupied: bool

    def get_child(self):
        return self.frame.get_child()

    def set_child(self, child):
        return self.frame.set_child(child)

    def on_drop(self, value: Gtk.DropTarget, data: str, x: float, y: float) -> None:
        if self.occupied:
            return
        print(f"drop: {value}, {data}, {x}, {y}")
        pos = json.loads(data)
        self.overview.move(self, (pos[0], pos[1]))

    def add_content(self) -> None:
        spec = self.spec
        if spec is None:
            self.frame.set_child(Gtk.Button(label="+"))
        else:
            widget = OverviewWidget(spec, self.overview.activity, self.draggable)
            widget.connect("spec-changed", self.on_spec_changed)
            self.frame.set_child(widget)
        self.occupied = spec is not None

    def on_spec_changed(self, source, data):
        self.emit("spec-changed", data)


class OverviewWidget(Widget):
    def __init__(
        self,
        spec: dict[str, str | float | int],
        activity: Activity | None,
        draggable=False,
    ):
        super().__init__(spec)
        self.activity = activity
        self.toolbar_view = Adw.ToolbarView()
        self.header = Adw.HeaderBar(
            show_start_title_buttons=False, show_end_title_buttons=False
        )
        settings_button = Gtk.Button.new_from_icon_name("open-menu-symbolic")
        settings_button.connect("clicked", self.open_settings)
        self.header.pack_end(settings_button)
        self.toolbar_view.add_top_bar(self.header)
        self.append(self.toolbar_view)

        if draggable:
            source = Gtk.DragSource()
            source.set_actions(Gdk.DragAction.MOVE)
            source.connect("prepare", self.on_prepare)
            self.add_controller(source)

        self.add_content()

    def on_prepare(self, drag_source: Gtk.DragSource, x: float, y: float):
        print(f"prepare: {drag_source}, {x}, {y}")
        frame = self.get_parent()
        assert isinstance(frame, Gtk.Frame)
        grid = frame.get_parent().get_parent()
        assert isinstance(grid, Gtk.Grid)
        pos = grid.query_child(frame.get_parent())
        return Gdk.ContentProvider.new_for_value(json.dumps(list(pos)))

    def add_content(self):
        spec = self.spec
        if "title" in spec:
            self.header.set_show_title(True)
            self.header.set_title_widget(Adw.WindowTitle(title=spec["title"]))
        else:
            self.header.set_show_title(False)
        if spec["type"] == "list":
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            self.toolbar_view.set_content(box)
            for item in spec["list"]:
                box.append(Gtk.Label(label=item))
        elif spec["type"] == "list.metrics":
            grid = Gtk.Grid(margin_start=5, margin_end=5)
            self.toolbar_view.set_content(grid)
            i = 0
            for item in spec["list"]:
                metric = get_metric(item)
                name = f"{metric.name}: "
                unit = metric.unit
                raw_value = self.activity.get_metric(metric)
                if raw_value is None:
                    continue
                format = metric.format
                if unit == "s":
                    raw_value = datetime.datetime.utcfromtimestamp(
                        0
                    ) + datetime.timedelta(seconds=float(raw_value))
                    format = "%H:%M:%S"
                    unit = ""
                value = f"{raw_value:{format}} "
                grid.attach(Gtk.Label(label=name, xalign=0), 0, i, 1, 1)
                grid.attach(Gtk.Label(label=value, xalign=1), 1, i, 1, 1)
                grid.attach(Gtk.Label(label=unit, xalign=0), 2, i, 1, 1)
                i += 1
        elif spec["type"] == "web":
            webview = WebKit.WebView()
            webview.load_uri(spec["link"])
            self.toolbar_view.set_content(webview)
            self.toolbar_view.set_vexpand(True)
        elif spec["type"] == "chart":
            x = self.activity.records_df.index
            y = self.activity.records_df[spec["column"]]
            fig = px.line(x=x, y=y)
            fig.update_layout(
                dict(
                    margin=dict(l=0, r=0, b=0, t=0),
                    yaxis=dict(visible=False, title=False),
                    xaxis=dict(visible=False, title=False),
                )
            )
            self.toolbar_view.set_content(
                FigureWebView(fig, dict(displayModeBar=False))
            )
            self.toolbar_view.set_vexpand(True)
        if "height" in spec:
            self.toolbar_view.set_size_request(-1, spec["height"])


def test(app):
    window = Adw.ApplicationWindow(application=app)
    spec = {
        "type": "grid",
        "list": [
            [
                {"type": "list", "list": ["a", "b"]},
                {"type": "list", "list": ["b", "b"]},
            ],
            [{"type": "list", "list": ["c", "b"]}],
        ]
    }
    window.set_content(OverviewPage(spec))
    window.present()


if __name__ == "__main__":
    app = Adw.Application()
    app.connect("activate", test)
    app.run()
