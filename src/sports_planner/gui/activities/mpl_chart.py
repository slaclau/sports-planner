import gi
import numpy as np
from matplotlib import gridspec
from matplotlib.pyplot import subplot
from matplotlib.widgets import MultiCursor, Slider, RangeSlider
from sports_planner_lib.athlete import Athlete
import pint
from sports_planner_lib.utils import format

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, Gio

from matplotlib.backends.backend_gtk4 import NavigationToolbar2GTK4 as NavigationToolbar

from matplotlib.backends.backend_gtk4agg import FigureCanvasGTK4Agg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter, MultipleLocator
import matplotlib.pyplot as plt

plt.style.use("./adwaita-dark.mplstyle")


class BasePlot(Gtk.Box):
    _row = 0
    _colors = plt.rcParams["axes.prop_cycle"]()
    _stacked_base_axis = None
    _text = None
    _x_formatter = None

    x_to_timedelta = True

    series = []
    _vlines = []
    _held = False
    _last_idx = None

    def __init__(self, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.params = kwargs
        fig = Figure()
        # Add canvas to vbox
        canvas = FigureCanvas(fig)  # a Gtk.DrawingArea
        canvas.set_hexpand(True)
        canvas.set_vexpand(True)
        scroller = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroller.set_child(canvas)
        self.append(scroller)
        canvas.mpl_connect("motion_notify_event", self.on_mouse_move)
        canvas.mpl_connect("button_press_event", self.on_click)

        # Create toolbar
        toolbar = NavigationToolbar(canvas)
        self.append(toolbar)

        self.fig = fig
        self.canvas = canvas

    def clear(self):
        self._row = 0
        self._colors = plt.rcParams["axes.prop_cycle"]()
        self._stacked_base_axis = None
        self._text = None
        self._x_formatter = None

        self.x_to_timedelta = True

        self.series = []
        self._vlines = []
        self._held = False
        self._last_idx = None

        self.fig.clf()

    def _set_cursor_visible(self, visible: bool) -> bool:
        need_redraw = self._text.get_visible() != visible
        self._text.set_visible(visible)
        for vline in self._vlines:
            vline.set_visible(visible)
        return need_redraw

    def on_mouse_move(self, event):
        if self._held:
            return
        if not event.inaxes:
            need_redraw = self._set_cursor_visible(False)
            if need_redraw:
                self.canvas.draw()
        else:
            self._set_cursor_visible(True)
            text = []
            for i in range(len(self.series)):
                series = self.series[i]
                idx = np.searchsorted(series["x"], event.xdata)
                if i == 0 and idx == self._last_idx:
                    return
                self._last_idx = idx
                if not text:
                    x_value = series["x"].iloc[idx]
                    text.append(format.time(x_value))
                y_value = series["y"].iloc[idx]

                self._vlines[i].set_xdata([event.xdata])

                _format = series["format"]
                if _format is None:
                    text.append(f"{series["name"]}: {y_value} {series["unit"]}")
                elif isinstance(_format, str):
                    text.append(
                        f"{series["name"]}: {y_value:{_format}} {series["unit"]}"
                    )
                else:
                    text.append(
                        f"{series["name"]}: {_format(y_value)} {series["unit"]}"
                    )
            self._text.set_text("\n".join(text))
            self._text.set_x(event.x)
            self._text.set_y(16 + self._stacked_base_axis.bbox.extents[3])
            self.canvas.draw()

    def on_click(self, event):
        self._held = not self._held
        self.on_mouse_move(event)

    def _set_stacked_base_axis(self, ax):
        self._stacked_base_axis = ax

        if self.x_to_timedelta:
            formatter = FuncFormatter(lambda t, pos: format.time(t))
            ax.xaxis.set_major_formatter(formatter)

            ax.xaxis.set_minor_locator(MultipleLocator(1 * 60))
        cb_registry = ax.callbacks
        cb_registry.connect("xlim_changed", self._xlim_changed)

        self._text = ax.annotate(
            "",
            (0, 0),
            xycoords="figure pixels",
            bbox=dict(facecolor="none", pad=4.0, edgecolor="white"),
        )

    def _xlim_changed(self, ax):
        [min_x, max_x] = ax.get_xlim()
        min_px = 40
        nt = round((ax.bbox.extents[3] - ax.bbox.extents[1]) / min_px)
        nt = min(10, max(5, nt))
        rough_dt = (max_x - min_x) / nt

        def get_base(v):
            return np.power(v, np.floor(np.log(rough_dt) / np.log(60)))

        def round_up(
            value: float, rounding_set: list[float], rev: bool = False
        ) -> float | int:
            # TODO: rev
            if value <= np.max(rounding_set):
                rtn = rounding_set[np.argwhere(np.array(rounding_set) > value)[0][0]]
                assert isinstance(rtn, float) or isinstance(rtn, int)
                return rtn
            return max(rounding_set)

        def round_dtick(rough_dt, base, rounding_set):
            rounded_val = round_up(rough_dt / base, rounding_set)
            return base * rounded_val

        base = get_base(60)
        dt = round_dtick(rough_dt, base, [2, 5, 10])

        ax.xaxis.set_major_locator(MultipleLocator(dt))

    def add_series(
        self,
        x,
        y,
        name="",
        unit="",
        color=None,
        next_plot=True,
        format=None,
    ):
        if self.x_to_timedelta:
            x = (x - x.iloc[0]).dt.seconds
        self.series.append(dict(x=x, y=y, name=name, unit=unit, format=format))
        color = color or next(self._colors)["color"]
        if next_plot:
            self._row += 1
            gs = gridspec.GridSpec(self._row, 1)

            # Reposition existing subplots
            for i, ax in enumerate(self.fig.axes):
                ax.set_position(gs[i].get_position(self.fig))
                ax.set_subplotspec(gs[i])

            # Add new subplot
            ax = self.fig.add_subplot(gs[self._row - 1], sharex=self._stacked_base_axis)
            if self._stacked_base_axis is None:
                self._set_stacked_base_axis(ax)
        else:
            ax = self.fig.axes[-1]

        ax.plot(x, y, color=color, label=name)
        ax.set_ylabel(name + f" ({unit})" if unit else name)
        ax.set_xlim([0, max(x)])

        self._vlines.append(ax.axvline(0, color="white", lw="0.8", visible=False))

        if self.fig.legends:
            self.fig.legends = []
        if self.params.get("show_legend", False):
            self.fig.legend()

        subplot_params = self.fig.subplotpars
        n = len(self.fig.axes)
        needed_height = (
            subplot_params.top
            + subplot_params.bottom
            + n * 200
            + (n - 1) * subplot_params.hspace
        )
        self.canvas.set_content_height(needed_height)


class ActivityPlot(BasePlot):
    columns_config = {
        "power": {"name": "Power", "unit": "W", "format": "0.0f"},
        "speed": {
            "name": "Speed",
            "unit": "km/h",
            "format": "0.1f",
            "from_unit": "m/s",
        },
        "pace": {
            "name": "Pace",
            "unit": "min/km",
            "format": lambda speed: format.time(1000 / speed, target="minutes"),
            "from_column": "speed",
        },
        "heartrate": {"name": "Heartrate", "unit": "bpm", "format": "0.0f"},
        "altitude": {"name": "Altitude", "unit": "m", "format": "0.0f"},
        "cadence": {"name": "Cadence", "unit": "rpm", "format": "0.0f"},
    }

    def __init__(self, name, context):
        super().__init__()

        self.settings = Gio.Settings(
            schema_id="io.github.slaclau.sports-planner.views.activities.tabs.activity-plot",
            path=f"/io/github/slaclau/sports-planner/views/activities/tabs/{name}/",
        )

        context.connect("activity-changed", self.on_activity_changed)
        self.settings.connect(
            "changed::columns", lambda s, _: self.on_activity_changed(context)
        )
        self.on_activity_changed(context)

    def on_activity_changed(self, context):
        self.clear()

        activity = context.activity
        df = activity.records_df

        columns = self.settings.get_value("columns").unpack()

        for column in columns:
            config = self.columns_config[column]
            df_column = config.get("from_column", column)
            if df_column not in df:
                continue
            x = df.timestamp
            y = df[df_column]
            if "from_unit" in config and "unit" in config:
                y = y * (
                    (1 * pint.get_application_registry().Unit(config["from_unit"]))
                    .to(config["unit"])
                    .m
                )
            self.add_series(
                x,
                y,
                name=config.get("name", df_column),
                unit=config.get("unit", ""),
                format=config.get("format", None),
            )


def on_activate(app):
    win = Adw.ApplicationWindow(application=app)
    plot = ActivityPlot("activity-plot", None)
    win.set_content(plot)

    ath = Athlete("seb.laclau@gmail.com")
    act = ath.activities[-1]
    act = ath.get_activity_full(act)

    plot.add_series(
        act.records_df.timestamp,
        act.records_df.power,
        name="Power",
        unit="W",
    )
    plot.add_series(
        act.records_df.timestamp, act.records_df.speed, name="Speed", unit="m/s"
    )
    plot.add_series(
        act.records_df.timestamp, act.records_df.altitude, name="Altitude", unit="m"
    )

    win.present()


if __name__ == "__main__":
    app = Adw.Application(application_id="org.gtk.Example")
    app.connect("activate", on_activate)
    app.run(None)
