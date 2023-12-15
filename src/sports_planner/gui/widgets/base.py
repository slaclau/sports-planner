"""Provides a base class for a widget specified by a dict."""
import tempfile
from abc import abstractmethod

import gi
import yaml

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, GObject, Gtk  # noqa: E402 PLC413

Spec = None | list["Spec"] | dict[str, "Spec"]


class Widget(Gtk.Box):
    """Base class for dict defined widget."""

    def __init__(self, spec: dict[str, Spec]):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        self.spec = spec

    @abstractmethod
    def add_content(self) -> None:
        pass

    class SettingsWindow(Adw.PreferencesWindow):
        def __init__(self, widget: "Widget"):
            super().__init__()
            self.widget = widget

            page = Adw.PreferencesPage()
            self.add(page)

            group = Adw.PreferencesGroup(title="Configuration YAML")
            page.add(group)
            self.text_buffer = Gtk.TextBuffer()

            configuration_field = self.make_configuration_field()
            group.add(configuration_field)

            self.connect("close-request", self.on_close)

        def on_close(self, _: Gtk.Widget) -> bool:
            try:
                self.check_and_save_spec()
                self.send_spec_changed()
                self.close()
                return False
            except yaml.YAMLError:
                return True

        def send_spec_changed(self) -> None:
            self.widget.emit("spec-changed", self.widget)

        def check_and_save_spec(self) -> None:
            file = tempfile.NamedTemporaryFile()
            with open(file.name, "w") as f:
                start = self.text_buffer.get_start_iter()
                end = self.text_buffer.get_end_iter()
                f.write(self.text_buffer.get_text(start, end, False))
            with open(file.name, "r") as f:
                spec = yaml.safe_load(f)
            self.widget.spec = spec
            self.widget.add_content()

        def make_configuration_field(self) -> Adw.PreferencesRow:
            row = Adw.PreferencesRow(title="Configuration YAML")
            text_view = Gtk.TextView(
                margin_start=5,
                margin_end=5,
                margin_top=5,
                margin_bottom=5,
                monospace=True,
                buffer=self.text_buffer,
            )
            text_view.set_size_request(-1, 100)
            file = tempfile.NamedTemporaryFile()
            with open(file.name, "w") as f:
                yaml.dump(self.widget.spec, f)
            with open(file.name, "r") as f:
                self.text_buffer.set_text(f.read())
            row.set_child(text_view)
            return row

    def open_settings(self, _: Gtk.Button) -> None:
        window = self.SettingsWindow(self)
        window.present()


GObject.signal_new(
    "spec_changed", Widget, GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_OBJECT,)
)
