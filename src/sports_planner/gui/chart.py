from tempfile import NamedTemporaryFile
from time import time

import gi

from sports_planner.utils.logging import logtime

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("WebKit", "6.0")
from gi.repository import WebKit  # noqa: E402


class FigureWebView(WebKit.WebView):
    def __init__(self, fig, conf=None):
        super().__init__()
        file = NamedTemporaryFile(mode="a")
        config = {"scrollZoom": True, "displaylogo": False}
        if conf is not None:
            for key in conf:
                config[key] = conf[key]
        with open(file.name, "w") as f:
            fig.write_html(f, config=config)
        with open(file.name, "r") as f:
            self.load_html(f.read())
