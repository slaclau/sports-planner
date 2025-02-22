import logging

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")

from gi.repository import Adw, Gtk, GLib


class LabelHandler(logging.Handler):
    def __init__(self, label: Gtk.Label, **kwargs):
        super().__init__(**kwargs)
        self.label = label

    def format(self, record):
        action_conversion = {
            "download": "Downloading",
            "compute_metrics": "Computing metrics for",
            "get_meanmaxes": "Getting Mean Max values for",
        }
        try:
            rtn = f"{action_conversion[record.action]} {record.activity.name if hasattr(record.activity, "name") else record.activity["name"]}"
            try:
                rtn += f" ({record.i} / {record.n})"
            except AttributeError:
                pass
            return rtn
        except AttributeError:
            return super().format(record)

    def emit(self, record):
        def log_func(record):
            self.label.set_label(self.format(record))
            return False

        GLib.timeout_add(0, lambda: log_func(record))


class ProgressBarHandler(logging.Handler):
    def __init__(self, progress_bar: Gtk.ProgressBar, **kwargs):
        super().__init__(**kwargs)
        self.progress_bar = progress_bar

    def emit(self, record):
        def log_func(record):
            try:
                self.progress_bar.set_fraction(record.i / record.n)
            except AttributeError:
                pass
            return False

        GLib.timeout_add(0, lambda: log_func(record))
