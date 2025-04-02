import datetime
import logging
import time

import gi
import numpy as np
import pint
import sweat
from sports_planner_lib.athlete import Athlete
from sports_planner_lib.metrics.pdm import DurationRegressor
from sports_planner_lib.utils import format

from sports_planner.utils.logging import log_debug_time

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
import matplotlib.pyplot as plt
from gi.repository import Adw, Gio, Gtk
from matplotlib import gridspec
from matplotlib.backends.backend_gtk4 import NavigationToolbar2GTK4 as NavigationToolbar
from matplotlib.backends.backend_gtk4agg import FigureCanvasGTK4Agg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter, MultipleLocator

plt.style.use("./adwaita-dark.mplstyle")

logger = logging.getLogger(__name__)


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
        # canvas.mpl_connect("button_press_event", self.on_click)

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

        self.series = []
        self._vlines = []
        self._held = False
        self._last_idx = None

        self.fig.clf()
        self.canvas.draw()

    def _set_cursor_visible(self, visible: bool) -> bool:
        if self._text is None:
            return False
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
                    if isinstance(series["x"], list) or isinstance(
                        series["x"], np.ndarray
                    ):
                        x_value = series["x"][idx]
                    else:
                        x_value = series["x"].iloc[idx]
                    text.append(format.time(x_value))
                if isinstance(series["y"], list) or isinstance(series["y"], np.ndarray):
                    y_value = series["y"][idx]
                else:
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
        fill_under=True,
        linestyle=None,
        marker=None,
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

        ax.plot(x, y, color=color, label=name, linestyle=linestyle, marker=marker)
        if fill_under:
            ax.fill_between(x, y, color=(color, 0.5))
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
        return ax


columns_config = {
    "power": {"name": "Power", "unit": "W", "format": "0.0f", "color": "#1A5FB4"},
    "speed": {
        "name": "Speed",
        "unit": "km/h",
        "format": "0.1f",
        "from_unit": "m/s",
        "color": "#26A269",
    },
    "pace": {
        "name": "Pace",
        "unit": "min/km",
        "format": lambda speed: format.time(1000 / speed, target="minutes"),
        "from_column": "speed",
        "color": "#E5A50A",
    },
    "heartrate": {
        "name": "Heartrate",
        "unit": "bpm",
        "format": "0.0f",
        "color": "#A51D2D",
    },
    "altitude": {
        "name": "Altitude",
        "unit": "m",
        "format": "0.0f",
        "color": "#63452C",
    },
    "cadence": {
        "name": "Cadence",
        "unit": "rpm",
        "format": "0.0f",
        "color": "#C64600",
    },
}


class ActivityPlot(BasePlot):

    def __init__(self, name, context):
        super().__init__()

        self.settings = Gio.Settings(
            schema_id="io.github.slaclau.sports-planner.tabs.activity-plot",
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
            if column == "altslope":
                if "altitude" in df:
                    self.plot_altslope(df)
                continue
            config = columns_config[column]
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
                color=config.get("color", None),
            )

    def plot_altslope(self, df):
        interval = 60
        sub_df = df.iloc[::interval].copy()
        sub_df["timedelta"] = (sub_df.timestamp - sub_df.timestamp.iloc[0]).dt.seconds
        scale = 36 / interval
        colors = ["#0F0", "#00F", "#FF0", "#F00", "#F00"]
        ax = self.add_series(
            sub_df.timestamp,
            sub_df.altitude,
            name="Alt/Slope",
            unit="m",
            format="0.1f",
            fill_under=False,
            color=columns_config["altitude"]["color"],
        )
        last_row = None
        for row in sub_df.itertuples():
            if last_row is None:
                last_row = row
                continue
            diff = row.altitude - last_row.altitude
            if diff < 0:
                ax.fill_between(
                    [last_row.timedelta, row.timedelta],
                    [last_row.altitude, row.altitude],
                    color=("#7F7F7F", 0.5),
                    edgecolor=None,
                )
            else:
                zone = int(diff * scale)
                if zone >= 4:
                    zone = 4
                ax.fill_between(
                    [last_row.timedelta, row.timedelta],
                    [last_row.altitude, row.altitude],
                    color=(colors[zone], 0.5),
                    edgecolor=None,
                )
            last_row = row


class CurvePlot(BasePlot):
    def __init__(self, name: str, context):
        super().__init__()
        self.x_to_timedelta = False
        self.settings = Gio.Settings(
            schema_id="io.github.slaclau.sports-planner.tabs.curve",
            path=f"/io/github/slaclau/sports-planner/views/activities/tabs/{name}/",
        )

        context.connect("activity-changed", self.on_activity_changed)
        self.settings.connect(
            "changed::columns", lambda s, _: self.on_activity_changed(context)
        )
        self.on_activity_changed(context)

    def on_activity_changed(self, context):
        period = {"days": 42}
        configured_model = "3 param"

        self.clear()
        activity = context.activity

        column = self.settings.get_string("column")
        if column not in activity.available_columns:
            return

        df = activity.meanmaxes_df

        y = df[f"mean_max_{column}"]

        date = activity.timestamp.date()
        t = time.time()
        historical = context.athlete.get_mean_max_for_period(
            column,
            activity.get_metric("Sport")["sport"],
            date - datetime.timedelta(**period),
            date + datetime.timedelta(days=1),
        )
        t = log_debug_time(t, "get hist")
        bests = context.athlete.get_bests_for_period(
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
        ax = self.add_series(
            x,
            predicted,
            next_plot=True,
            name="Predicted",
            fill_under=True,
            color=columns_config[column]["color"],
        )
        self.add_series(
            x,
            y,
            next_plot=False,
            name="Actual",
            fill_under=False,
            color=columns_config[column]["color"],
            linestyle="--",
        )
        self.add_series(
            historical.duration,
            historical[f"mean_max_{column}"],
            next_plot=False,
            name="Historical",
            fill_under=False,
            linestyle="",
        )
        self.add_series(
            bests.duration,
            bests[f"mean_max_{column}"],
            next_plot=False,
            name="Bests",
            fill_under=False,
            linestyle="",
            marker="o",
            color="white",
        )
        ax.set_ylabel(columns_config[column]["name"])
        ax.set_xscale("log")

        param_map = {"cp": "Critical Power", "w_prime": "W'", "p_max": "Maximum Power"}
        param_units = {"cp": "W", "w_prime": "kJ", "p_max": "W"}
        power_formatter = lambda p: f"{p:0.0f}"
        param_formatters = {
            "cp": power_formatter,
            "w_prime": lambda w: f"{w / 1000:0.1f}",
            "p_max": power_formatter,
        }
        text_str = "<br>".join(
            [
                f"{param_map[param]}: {param_formatters[param](value)} {param_units[param]}"
                for param, value in params.items()
            ]
        )

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

        ax.set_xticks(ticks, labels=ticklabels)
        ax.set_xticks([], minor=True)
        ax.set_xlim([1, max(max(x), 1800)])


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
