import logging
import sys
import threading

import gi

from sports_planner.athlete import Athlete
from sports_planner.gui import dialogues
from sports_planner.gui.main import MainWindow
from sports_planner.io.sync.garmin import Garmin, LoginException
from sports_planner.metrics.garmin import RunningVO2Max
from sports_planner.metrics.pmc import PMC, Banister, UniversalStressScore

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
import pandas as pd
from gi.repository import Adw, GLib


class Application(Adw.Application):
    """Main class for application."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect("activate", self.on_activate)
        self.win: MainWindow | None = None
        self.sync_providers = []
        self.athlete = None
        self.current_athlete = "seb.laclau@gmail.com"
        self.password = None

        self.on_sync_funcs = []

    def test(self):
        athlete = Athlete(self.current_athlete)
        # print(athlete.test())

    def on_activate(self, app):
        self.win = MainWindow(application=app)
        self.win.present()
        self.login()
        self.create_athlete()

    def _thread_func(self):
        self.athlete = Athlete(
            self.current_athlete,
            callback_func=self._athlete_callback_func,
            sync_providers=self.sync_providers,
        )
        GLib.idle_add(self.win.activities_view.when_athlete_ready)
        self.athlete.get_workouts_and_seasons()
        GLib.idle_add(self.win.planning_view.when_athlete_ready)

        self.win.performance_view.data = {
            "pmc": ("Creating PMC", "PMC"),
            "banister": ("Waiting for PMC to be ready", "Banister"),
        }
        GLib.idle_add(self.win.performance_view.when_data_ready)

        pmc = PMC(
            self.athlete,
            UniversalStressScore,
            title="PMC",
            callback_func=lambda *args: self._performance_callback_func("pmc", *args),
        )
        self.win.performance_view.data["pmc"] = pmc
        GLib.idle_add(self.win.performance_view.when_data_ready)

        banister = Banister(
            pmc,
            RunningVO2Max,
            title="Banister",
            callback_func=lambda *args: self._performance_callback_func(
                "banister", *args
            ),
        )
        self.win.performance_view.data["banister"] = banister
        GLib.idle_add(self.win.performance_view.when_data_ready)

    def _athlete_callback_func(self, status, *args):
        GLib.idle_add(self.win.activities_view.status_update, status, *args)
        GLib.idle_add(self.win.performance_view.status_update, status, *args)
        GLib.idle_add(self.win.planning_view.status_update, status, *args)

    def _performance_callback_func(self, page, status, *args):
        GLib.idle_add(self.win.performance_view.update_status_page, page, status, *args)

    def create_athlete(self):
        thread = threading.Thread(target=self._thread_func, daemon=True)
        thread.start()

    def register_on_sync_func(self, func):
        self.on_sync_funcs.append(func)

    def sync(self, widget):
        thread = threading.Thread(target=self._sync, daemon=True)
        thread.start()

    def _sync(self):
        self.login().sync()
        self.create_athlete()

    def login(self):
        try:
            athlete = Garmin(self.current_athlete)
            self.sync_providers.append(athlete)
            return athlete
        except LoginException:
            dialogue = dialogues.PasswordDialogue()
            dialogue.connect("response", self.get_password)

    def get_password(self, dialogue, response_id):
        password = dialogue.get_password()
        garmin = Garmin(self.current_athlete, password)
        garmin.sync()


def main():
    """Entrypoint"""
    logging.basicConfig(level=logging.INFO)
    pd.set_option("display.max_rows", None)
    # pd.set_option("display.max_columns", None)
    app = Application(application_id="io.github.slaclau.sports_planner")
    app.run(sys.argv)


if __name__ == "__main__":
    main()
