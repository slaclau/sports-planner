import sys
from pathlib import Path

import gi
import yaml

from sports_planner.io.files import Activity

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from sports_planner.gui.activities.activity import ActivityView


def main(app, file=None):
    window = Adw.Window(title="Activity Viewer", application=app)

    window.present()

    dlg = Gtk.FileDialog(title="Select activity")

    def callback(dlg, result):
        file = dlg.open_finish(result)

        with open(
            Path.home()
            / "sports-planner"
            / "seb.laclau@gmail.com"
            / "config"
            / "activity.yaml"
        ) as f:
            spec = yaml.safe_load(f)

        activity = Activity(file.get_path())

        window.set_content(ActivityView(activity, spec))

    if file is None:
        dlg.open(window, None, callback)
    else:
        with open(
            Path.home()
            / "sports-planner"
            / "seb.laclau@gmail.com"
            / "config"
            / "activity.yaml"
        ) as f:
            spec = yaml.safe_load(f)
        activity = Activity(file)
        window.set_content(ActivityView(activity, spec))


def standalone(*args):
    app = Adw.Application(
        application_id="io.github.slaclau.sports_planner.activity_viewer"
    )
    app.connect("activate", lambda app: main(app, args[1]))
    app.run()


if __name__ == "__main__":
    standalone(*sys.argv)
