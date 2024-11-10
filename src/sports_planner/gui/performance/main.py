import datetime
import logging

import gi
import pandas as pd

from sports_planner.metrics.pmc import PMC, Banister

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
import plotly.graph_objects as go
from gi.repository import Adw, Gtk
from plotly_gtk.webview import FigureWebView

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)


class PerformanceView(Gtk.Box):
    def __init__(self, application):
        super().__init__()
        self.application = application
        self.data = None

        self.view = Adw.ToolbarView()
        self.view.set_hexpand(True)
        self.view.set_vexpand(True)

        self.append(self.view)

        self.performance_stack = Gtk.Stack()
        performance_switcher = Gtk.StackSwitcher(stack=self.performance_stack)
        self.view.add_top_bar(performance_switcher)

        self.status_page = Adw.StatusPage(title="Waiting for activities to be loaded")
        self.view.set_content(self.status_page)

    def status_update(self, text: str, i: int = 0, n: int = 0):
        self.status_page.bar = Gtk.ProgressBar()
        if n > 0:
            self.status_page.set_description(text)
            self.status_page.set_child(self.status_page.bar)
            self.status_page.bar.set_fraction(i / n)
        self.status_page.set_description(text)

    def when_data_ready(self):
        self.view.set_content(self.performance_stack)
        self.add_charts(self.data)
        self.application.register_on_sync_func(self.update)

    def create_pmc(self, pmc):
        df = pmc.df.round(
            {
                "impulse": 0,
                "sts": 1,
                "lts": 1,
                "rr": 1,
                "tsb": 1,
                "future_impulse": 0,
                "predicted_sts": 1,
                "predicted_lts": 1,
                "predicted_rr": 1,
                "predicted_tsb": 1,
            }
        )
        fig = go.Figure()
        x = pd.date_range(df.index[0], datetime.date.today())
        for col, colour, name in zip(
            ["sts", "lts", "tsb", "rr"],
            ["red", "blue", "orange", "lightblue"],
            [
                "Short term stress",
                "Long term stress",
                "Training stress balance",
                "Ramp rate",
            ],
        ):
            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=df.loc[x, col],
                    mode="lines",
                    name=name,
                    yaxis="y",
                    line_color=colour,
                    hoverlabel={"namelength": -1},
                )
            )
        x = pd.date_range(
            datetime.date.today() - datetime.timedelta(days=1), df.index[-1]
        )
        for col, colour, name in zip(
            ["predicted_sts", "predicted_lts", "predicted_tsb", "predicted_rr"],
            ["red", "blue", "orange", "lightblue"],
            [
                "Short term stress (predicted)",
                "Long term stress (predicted)",
                "Training stress balance (predicted)",
                "Ramp rate (predicted)",
            ],
        ):
            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=df.loc[x, col],
                    mode="lines",
                    name=name,
                    yaxis="y",
                    line=dict(color=colour, dash="dot"),
                    hoverlabel={"namelength": -1},
                )
            )
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df["impulse"],
                yaxis="y2",
                name=pmc.metric.name,
                hoverlabel={"namelength": -1},
            )
        )
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df["future_impulse"],
                yaxis="y2",
                name=f"{pmc.metric.name} (planned)",
                hoverlabel={"namelength": -1},
            )
        )
        for date in self.application.athlete.seasons:
            fig.add_vline(x=date[0], line_color="green")
            if date != self.application.athlete.seasons[-1]:
                fig.add_vline(x=date[1], line_color="red")
        end_date = datetime.date.today() + datetime.timedelta(days=pmc.t_short)
        start_date = datetime.date.today() - datetime.timedelta(days=pmc.t_long)

        fig.add_hrect(y0=-100, y1=-30, line_width=0, fillcolor="red", opacity=0.2)
        fig.add_hrect(y0=-30, y1=-10, line_width=0, fillcolor="green", opacity=0.2)
        fig.add_hrect(y0=-10, y1=5, line_width=0, fillcolor="grey", opacity=0.2)
        fig.add_hrect(y0=5, y1=25, line_width=0, fillcolor="blue", opacity=0.2)
        fig.add_hrect(y0=25, y1=100, line_width=0, fillcolor="orange", opacity=0.2)

        fig.update_layout(
            **{
                "xaxis": dict(
                    range=[start_date, end_date], rangeslider=dict(visible=True)
                ),
                "yaxis": dict(range=[-40, 100], title="load"),
                "yaxis2": dict(
                    overlaying="y",
                    side="right",
                    autoshift=True,
                    anchor="free",
                    showgrid=False,
                    title=pmc.metric.name,
                    showticklabels=False,
                ),
                "hovermode": "x unified",
            }
        )
        return FigureWebView(fig)

    def create_banister(self, banister):
        df = banister.df.round(
            {
                "impulse": 0,
                "sts": 1,
                "lts": 1,
                "tsb": 1,
                "response": 2,
                "future_predict": 2,
            }
        )
        fig = go.Figure()
        x = pd.date_range(df.index[0], datetime.date.today())
        for col, colour, name in zip(
            ["sts", "lts"],
            ["red", "blue"],
            ["Short term stress", "Long term stress"],
        ):
            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=df.loc[x, col],
                    mode="lines",
                    name=name,
                    yaxis="y",
                    line_color=colour,
                    hoverlabel={"namelength": -1},
                )
            )
        x = pd.date_range(
            datetime.date.today() - datetime.timedelta(days=1), df.index[-1]
        )
        for col, colour, name in zip(
            ["predicted_sts", "predicted_lts"],
            ["red", "blue"],
            ["Short term stress (predicted)", "Long term stress (predicted)"],
        ):
            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=df.loc[x, col],
                    mode="lines",
                    name=name,
                    yaxis="y",
                    line=dict(color=colour, dash="dot"),
                    hoverlabel={"namelength": -1},
                )
            )
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df["impulse"],
                yaxis="y2",
                name=banister.pmc.metric.name,
                hoverlabel={"namelength": -1},
            )
        )
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df["future_impulse"],
                yaxis="y2",
                name=f"{banister.pmc.metric.name} (planned)",
                hoverlabel={"namelength": -1},
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["response"],
                yaxis="y3",
                mode="lines",
                name=banister.metric.name,
                connectgaps=True,
                hoverlabel={"namelength": -1},
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["future_predict"],
                yaxis="y3",
                mode="lines",
                name="Prediction",
                hoverlabel={"namelength": -1},
            )
        )
        for date in self.application.athlete.seasons:
            fig.add_vline(x=date[0], line_color="green")
            if date != self.application.athlete.seasons[-1]:
                fig.add_vline(x=date[1], line_color="red")
        end_date = datetime.date.today() + datetime.timedelta(days=banister.pmc.t_short)
        start_date = datetime.date.today() - datetime.timedelta(
            days=banister.pmc.t_long
        )

        fig.update_layout(
            **{
                "xaxis": dict(
                    range=[start_date, end_date], rangeslider=dict(visible=True)
                ),
                "yaxis": dict(range=[-40, 100], title="load"),
                "yaxis2": dict(
                    overlaying="y",
                    side="right",
                    autoshift=True,
                    anchor="free",
                    showgrid=False,
                    title=banister.pmc.metric.name,
                    showticklabels=False,
                ),
                "yaxis3": dict(
                    overlaying="y",
                    side="right",
                    autoshift=True,
                    anchor="free",
                    showgrid=False,
                    title=banister.metric.name,
                    showticklabels=True,
                ),
                "hovermode": "x unified",
            }
        )
        return FigureWebView(fig)

    def update(self):
        self.add_charts(list(self.data))

    def update_page(self, page):
        self._add_chart(page)

    def update_status_page(self, page_name, text: str, i: int = 0, n: int = 0):
        logger.debug(f"Updating status page {page_name} with {text}, {i}, {n}")
        page = self.performance_stack.get_child_by_name(page_name)
        if isinstance(page, Adw.StatusPage):
            bar = Gtk.ProgressBar()
            if n > 0:
                page.set_child(bar)
                bar.set_fraction(i / n)
            page.set_description(text)

    def add_charts(self, names):
        for name in names:
            self._add_chart(name)

    def _add_chart(self, name):
        logger.debug(f"Adding {name}: {self.data[name]} to performance view")
        old_page = self.performance_stack.get_child_by_name(name)
        data = self.data[name]
        if old_page is not None:
            logger.debug("Removing old page")
            self.performance_stack.remove(old_page)
        if isinstance(data, PMC):
            logger.debug("Adding PMC")
            self.performance_stack.add_titled(self.create_pmc(data), name, data.title)
        elif isinstance(data, Banister):
            logger.debug("Adding Banister")
            self.performance_stack.add_titled(
                self.create_banister(data), name, data.title
            )
        elif isinstance(data, tuple):
            logger.debug("Adding Status page")
            self.performance_stack.add_titled(
                Adw.StatusPage(title=data[0]), name, data[1]
            )
