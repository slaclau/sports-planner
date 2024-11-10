from typing import TYPE_CHECKING

import gi

from sports_planner.gui.activities.main import ActivitiesView
from sports_planner.gui.performance.main import PerformanceView
from sports_planner.gui.planning.main import PlanningView
from sports_planner.gui.training.main import TrainingView

if TYPE_CHECKING:
    from sports_planner.main import Application

gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk


class MainWindow(Adw.ApplicationWindow):
    """Main window for application."""

    def __init__(self, application: "Application") -> None:
        super().__init__(title="Sports Planner", application=application)
        self.maximize()

        self.application = application
        self.main_view = Adw.ToolbarView()
        self.header = Adw.HeaderBar()
        self.main_view.add_top_bar(self.header)
        self.set_content(self.main_view)

        self.main_stack = Gtk.Stack()
        self.main_view.set_content(self.main_stack)

        self.home_button = Gtk.Button(icon_name="user-home-symbolic")
        self.home_button.connect(
            "clicked", lambda _: self.main_stack.set_visible_child(self.home_view)
        )
        self.header.pack_start(self.home_button)

        self.sync_button = Gtk.Button(label="Sync")
        self.sync_button.connect("clicked", self.application.sync)
        self.header.pack_start(self.sync_button)

        # Activities
        self.activities_view = ActivitiesView(self.application)
        self.main_stack.add_child(self.activities_view)

        # Performance
        self.performance_view = PerformanceView(self.application)
        self.main_stack.add_child(self.performance_view)

        # Planning
        self.planning_view = PlanningView(self.application)
        self.main_stack.add_child(self.planning_view)

        # Planning
        self.training_view = TrainingView(self.application)
        self.main_stack.add_child(self.training_view)

        # Home
        self.home_view = Gtk.Grid()
        self.home_view.set_column_homogeneous(True)
        self.home_view.set_row_homogeneous(True)
        self.home_view.set_column_spacing(10)
        self.home_view.set_row_spacing(10)
        self.main_stack.add_child(self.home_view)

        self.activities_button = Gtk.Button(label="Activities")
        self.home_view.attach(self.activities_button, 0, 0, 1, 1)
        self.activities_button.connect(
            "clicked",
            lambda _: self.main_stack.set_visible_child(self.activities_view),
        )

        self.performance_button = HomeButton("power-profile-performance-symbolic")
        self.home_view.attach(self.performance_button, 1, 0, 1, 1)
        self.performance_button.connect(
            "clicked",
            lambda _: self.main_stack.set_visible_child(self.performance_view),
        )

        self.planning_button = HomeButton("calendar-month-symbolic")
        self.home_view.attach(self.planning_button, 0, 1, 1, 1)
        self.planning_button.connect(
            "clicked",
            lambda _: self.main_stack.set_visible_child(self.planning_view),
        )

        self.training_button = Gtk.Button(label="Training")
        self.home_view.attach(self.training_button, 1, 1, 1, 1)
        self.training_button.connect(
            "clicked",
            lambda _: self.main_stack.set_visible_child(self.training_view),
        )

        self.main_stack.set_visible_child(self.home_view)


class HomeButton(Gtk.Button):
    def __init__(self, icon_name: str):
        super().__init__()
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(256)
        self.set_child(icon)
