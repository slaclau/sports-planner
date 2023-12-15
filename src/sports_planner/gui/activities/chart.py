import plotly.express as px  # type: ignore
import plotly.graph_objects as go  # type: ignore
import plotly.io as pio  # type: ignore
import sweat  # type: ignore

from sports_planner.gui.chart import FigureWebView
from sports_planner.gui.widgets.base import Spec, Widget
from sports_planner.io.files import Activity


class MapViewer(Widget):
    def __init__(self, spec: dict[str, Spec], activity: Activity):
        super().__init__(spec)
        self.activity = activity
        self.add_content()

    def add_content(self) -> None:
        zoom = (
            self.spec["zoom"] if self.spec is not None and "zoom" in self.spec else 13
        )
        mapbox_style = (
            self.spec["open-street-map"]
            if self.spec is not None and "mapbox_style" in self.spec
            else "open-street-map"
        )
        fig = px.line_mapbox(
            self.activity.records_df,
            lat="latitude",
            lon="longitude",
            mapbox_style=mapbox_style,
            zoom=zoom,
        )
        webview = FigureWebView(fig)
        webview.set_vexpand(True)
        webview.set_hexpand(True)
        self.append(webview)


class ActivityPlot(Widget):
    def __init__(self, spec: dict[str, Spec], activity: Activity):
        super().__init__(spec)
        self.activity = activity
        self.add_content()

    def add_content(self) -> None:
        columns = self.spec["columns"]
        df = self.activity.records_df
        columns = set(df.columns).intersection(columns)
        fig = go.Figure()
        i = 0
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

        webview = FigureWebView(fig)
        webview.set_vexpand(True)
        webview.set_hexpand(True)
        self.append(webview)
