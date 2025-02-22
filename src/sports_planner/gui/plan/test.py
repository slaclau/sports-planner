#!/usr/bin/env python3

import gi
from gi.repository import Adw, Gcal, Gtk, GLib


def main(app):
    window = Adw.Window(title="Test", application=app)
    calendar = Gcal.MonthView()

    tz = GLib.TimeZone.new_local()
    calendar.props.active_date = GLib.DateTime(tz, 2023, 1, 28, 0, 0, 0)

    css_provider = Gtk.CssProvider()
    css_provider.load_from_path("style.css")
    Gtk.StyleContext.add_provider_for_display(
        calendar.get_display(),
        css_provider,
        Gtk.STYLE_PROVIDER_PRIORITY_USER,
    )
    calendar.add_event()
    calendar.emit("create-event", calendar.get_range(), 1, 10)

    window.set_content(calendar)
    window.present()


def standalone():
    app = Adw.Application(application_id="io.github.slaclau.sports_planner.ant_trainer")
    app.connect("activate", main)
    app.run()


if __name__ == "__main__":
    standalone()
