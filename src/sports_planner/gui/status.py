import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa E402


class StatusPage(Gtk.Box):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.status_page = Adw.StatusPage(title=title)
        self.status_page.set_hexpand(True)
        self.status_page.set_vexpand(True)
        self.append(self.status_page)
        self.bar = Gtk.ProgressBar()

    def update(self, text: str, i: int = 0, n: int = 0) -> None:
        self.status_page.set_child(None)
        if n > 0:
            self.status_page.set_description(text)
            self.status_page.set_child(self.bar)
            self.bar.set_fraction(i / n)
        self.status_page.set_description(text)
