"""Entrypoint to program, creates custom Adwaita Application class."""
import cProfile
import logging
import sys
import threading
import typing

import gi
import profilehooks

gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk  # noqa: E402

from sports_planner.athlete import Athlete
from sports_planner.gui import dialogues
from sports_planner.gui.main import MainWindow
from sports_planner.io.sync.base import SyncProvider
from sports_planner.io.sync.garmin import Garmin, LoginException
from sports_planner.metrics.garmin import RunningVO2Max
from sports_planner.metrics.pmc import PMC, Banister, UniversalStressScore


class Application(Adw.Application):
    """Main class for application."""

    def __init__(self) -> None:
        super().__init__(application_id="io.github.slaclau.sports_planner")
        self.connect("activate", self.on_activate)
        self.win: MainWindow | None = None
        self.sync_providers: list[SyncProvider] = []
        self.athlete: Athlete | None = None
        self.current_athlete = "seb.laclau@gmail.com"
        self.password: str | None = None

        self.on_sync_funcs: list[typing.Callable[[], None]] = []

    def on_activate(self, app: "Application") -> None:
        self.win = MainWindow(application=app)
        self.win.present()
        self.login()
        self.create_athlete()

    @profilehooks.profile(filename="_thread_func.prof", immediate=True)
    def _thread_func(self) -> None:
        if isinstance(self.win, MainWindow):
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
                callback_func=lambda *args: self._performance_callback_func(
                    "pmc", *args
                ),
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
        else:
            raise TypeError

    def _athlete_callback_func(self, text: str, i: int = 0, n: int = 0) -> None:
        if isinstance(self.win, MainWindow):
            GLib.idle_add(self.win.activities_view.status_update, text, i, n)
            GLib.idle_add(self.win.performance_view.status_update, text, i, n)
            GLib.idle_add(self.win.planning_view.status_update, text, i, n)
        else:
            raise TypeError

    def _performance_callback_func(
        self, page: str, status: str, *args: list[str | int]
    ) -> None:
        if isinstance(self.win, MainWindow):
            GLib.idle_add(
                self.win.performance_view.update_status_page, page, status, *args
            )
        else:
            raise TypeError

    def create_athlete(self) -> None:
        thread = threading.Thread(target=self._thread_func, daemon=True)
        thread.start()

    def register_on_sync_func(self, func: typing.Callable[[], None]) -> None:
        self.on_sync_funcs.append(func)

    def sync(self, widget: Gtk.Widget) -> None:
        thread = threading.Thread(target=self._sync, daemon=True)
        thread.start()

    def _sync(self) -> None:
        self.login()
        for sync_provider in self.sync_providers:
            sync_provider.sync()
        self.create_athlete()

    def login(self) -> bool:
        try:
            athlete = Garmin(self.current_athlete)
            self.sync_providers.append(athlete)
            return True
        except LoginException:
            dialogue = dialogues.PasswordDialogue()
            dialogue.connect("response", self.get_password)
        return False

    def get_password(
        self, dialogue: dialogues.PasswordDialogue, response_id: int
    ) -> None:
        password = dialogue.get_password()
        garmin = Garmin(self.current_athlete, password)
        self.sync_providers.append(garmin)


def main() -> None:
    """Entrypoint"""
    logging.basicConfig(level=logging.WARNING)
    # pd.set_option("display.max_rows", None)
    # pd.set_option("display.max_columns", None)
    app = Application()
    app.run(sys.argv)


if __name__ == "__main__":
    main()
