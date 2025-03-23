import logging

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, Gtk, Gdk

from sports_planner.gui.app import Context
from sports_planner.gui.logging import LabelHandler, ProgressBarHandler
from sports_planner.main import INSTALL_TYPE
from sports_planner.gui.train.main import TrainingView
from sports_planner.gui.activities.view import ActivitiesView
from sports_planner.gui.plan.view import PlanView

logger = logging.getLogger(__name__)


@Gtk.Template(resource_path="/io/github/slaclau/sports-planner/gtk/main.ui")
class SportsPlannerWindow(Adw.ApplicationWindow):
    __gtype_name__ = "SportsPlannerWindow"

    main_tab_view = Gtk.Template.Child("main-tab-view")
    home_page: Adw.TabPage = Gtk.Template.Child("home-page")
    athletes_page: Adw.TabPage = Gtk.Template.Child("athletes-page")
    activities_page: Adw.TabPage = Gtk.Template.Child("activities-page")
    performance_page: Adw.TabPage = Gtk.Template.Child("performance-page")
    plan_page: Adw.TabPage = Gtk.Template.Child("plan-page")
    train_page: Adw.TabPage = Gtk.Template.Child("train-page")
    train_box: Gtk.Box = Gtk.Template.Child("train-box")

    activities_view = Gtk.Template.Child("activities-view")
    plan_view = Gtk.Template.Child("plan-view")

    sync_button: Gtk.Button = Gtk.Template.Child("sync-button")
    sync_label: Gtk.Label = Gtk.Template.Child("sync-label")
    sync_progress: Gtk.ProgressBar = Gtk.Template.Child("sync-progress")

    sync_task: Gio.Task

    def __init__(self, context: Context | None = None, **kwargs):
        super().__init__(**kwargs)

        self.context = context

        self._add_standard_actions()

        self._create_go_action("go-home", self.home_page)
        self._create_go_action("go-athletes", self.athletes_page)
        self._create_go_action("go-activities", self.activities_page)
        self._create_go_action("go-performance", self.performance_page)
        self._create_go_action("go-plan", self.plan_page)
        self._create_go_action("go-train", self.train_page)

        self.activities_view.set_context(context)
        self.plan_view.set_context(context)

        self.train_box.append(TrainingView())

        athlete_logger = logging.getLogger("sports_planner_lib.athlete")
        athlete_logger.addHandler(LabelHandler(self.sync_label, level=logging.INFO))
        athlete_logger.addHandler(
            ProgressBarHandler(self.sync_progress, level=logging.INFO)
        )
        logger.debug("window created")

    def _sync(self):
        self.sync_button.set_sensitive(False)
        self.sync_progress.set_visible(True)

        def on_sync_done(task, _):
            self.sync_button.set_sensitive(True)
            self.sync_label.set_label("")
            self.sync_progress.set_visible(False)

            self.activities_view.set_context(self.context)
            self.plan_view.set_context(self.context)

            notification = Gio.Notification()
            notification.set_title("Sync completed")
            notification.set_body(
                "Sports Planner has finished synchronizing activities"
            )

            self.get_application().send_notification("sync-done", notification)

        def sync_cb(task, object, _, __):
            self.context.athlete.import_activities(redownload=False)
            self.context.athlete.update_db(recompute=False)

        self.sync_task = Gio.Task.new(callback=on_sync_done)
        self.sync_task.run_in_thread(sync_cb)

    def _add_standard_actions(self):
        action_entries = [
            (
                "sync",
                lambda action, parameter, data: self._sync(),
            ),
        ]
        if self.context.install_type == INSTALL_TYPE.WHEEL:
            pass
        else:
            action_entries.append(
                (
                    "show-help",
                    lambda action, parameter, data: Gtk.show_uri(
                        self, "help:sports-planner", Gdk.CURRENT_TIME
                    ),
                ),
            )
        self.add_action_entries(action_entries)

    def _create_go_action(self, name, page):
        action = Gio.SimpleAction.new(name, None)
        action.connect(
            "activate", lambda act, _: self.main_tab_view.set_selected_page(page)
        )
        self.add_action(action)
