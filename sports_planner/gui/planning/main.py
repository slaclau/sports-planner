import datetime
import logging

import gi

from sports_planner.gui.activities.main import ActivitiesView

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk


class PlanningView(Gtk.Box):
    def __init__(self, application):
        super().__init__()
        self.application = application
        self.data = None

        self.view = Adw.ToolbarView()
        self.view.set_hexpand(True)
        self.view.set_vexpand(True)

        self.append(self.view)

        self.stack = Gtk.Stack()
        switcher = Gtk.StackSwitcher(stack=self.stack)
        self.view.add_top_bar(switcher)

        self.status_page = Adw.StatusPage(title="Waiting for activities to be loaded")
        self.view.set_content(self.status_page)

        self.calendar = None
        self.calendar_sidebar = None

    def status_update(self, status, *args):
        self.status_page.bar = Gtk.ProgressBar()
        if status == "load":
            i = args[0]
            n = args[1]
            self.status_page.set_description(f"Activity {i} of {n} loaded")
            self.status_page.set_child(self.status_page.bar)
            self.status_page.bar.set_fraction(i / n)
        elif status == "text":
            self.status_page.set_description(args[0])
            self.status_page.set_child(None)

    def when_athlete_ready(self):
        self.view.set_content(self.stack)
        self.add_calendar()

    def add_calendar(self):
        navigation_view = Adw.OverlaySplitView(sidebar_position=Gtk.PackType.END)
        self.calendar = Gtk.Calendar()
        self.calendar_sidebar = Adw.NavigationPage()
        navigation_view.set_content(Adw.NavigationPage(child=self.calendar))
        navigation_view.set_sidebar(self.calendar_sidebar)
        self.stack.add_child(navigation_view)

        for signal in ["next-month", "prev-month", "next-year", "prev-year"]:
            self.calendar.connect(signal, self.update_calendar)
        self.calendar.connect("day-selected", self.show_activities_for_day)

        self.update_calendar(None)

    def update_calendar(self, _):
        self.calendar.clear_marks()
        month = self.calendar.get_date().get_month()
        year = self.calendar.get_date().get_year()
        start = datetime.datetime(year=year, month=month, day=1)
        if month == 12:
            month = 0
            year += 1
        end = datetime.datetime(year=year, month=month + 1, day=1)

        self.calendar.activities = self.application.athlete.days.loc[
            self.application.athlete.days.index >= start
        ]
        self.calendar.activities = self.calendar.activities.loc[
            self.calendar.activities.index < end
        ]

        self.calendar.workouts = self.application.athlete.workouts.loc[
            self.application.athlete.workouts["date"] >= start
        ]
        self.calendar.workouts = self.calendar.workouts.loc[
            self.calendar.workouts["date"] < end
        ]

        for day in self.calendar.activities.index:
            self.calendar.mark_day(day.day)

        for day in self.calendar.workouts["date"]:
            self.calendar.mark_day(day.day)

    def show_activities_for_day(self, _):
        date = self.calendar.get_date()
        date = datetime.date(*date.get_ymd())
        self.calendar_sidebar.set_child(None)
        self.calendar.activities_list = Gtk.ListBox()
        self.calendar.activities_list.add_css_class("navigation-sidebar")
        self.calendar_sidebar.set_child(self.calendar.activities_list)
        self.calendar.activities_list.connect("row-activated", self.display_activity)

        try:
            workout = self.calendar.workouts.loc[date, "name"]
            row = Gtk.ListBoxRow(child=Gtk.Label(label=workout))
            row.workout = self.calendar.workouts.loc[date, "scheduleId"]
            self.calendar.activities_list.append(row)
        except KeyError:
            logging.debug(f"No activities on {date}")

        try:
            activities = self.calendar.activities.loc[date, "activities"]
            for activity in activities:
                self.calendar.activities_list.append(
                    ActivitiesView.create_activity_row(activity)
                )
        except KeyError:
            logging.debug(f"No activities on {date}")

    def display_activity(self, _, row):
        try:
            self.application.win.activities_view.display_activity(_, row)
        except AttributeError:
            page = Gtk.Label(label=row.workout)
            self.application.win.activities_view.navigation_content_view.set_content(
                page
            )

        self.application.win.main_stack.set_visible_child(
            self.application.win.activities_view
        )
