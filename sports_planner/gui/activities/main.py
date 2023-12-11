import datetime
import json
import logging
import os

import gi
import pandas as pd

from sports_planner.io.files import Activity

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, Pango

from sports_planner.gui.activities.activity import ActivityView


class ActivitiesView(Gtk.Box):
    def __init__(self, application):
        super().__init__()
        self.application = application

        navigation_split_view = Adw.NavigationSplitView()
        navigation_split_view.set_hexpand(True)
        navigation_split_view.set_vexpand(True)

        self.append(navigation_split_view)

        navigation_sidebar = Adw.NavigationPage(title="Activities")
        self.navigation_content = Adw.NavigationPage(title="Select an activity")
        navigation_split_view.set_sidebar(navigation_sidebar)
        navigation_split_view.set_content(self.navigation_content)

        navigation_sidebar_view = Adw.ToolbarView()
        navigation_sidebar_stack = Gtk.Stack()
        navigation_sidebar_header = Gtk.StackSwitcher(stack=navigation_sidebar_stack)
        navigation_sidebar_view.set_content(navigation_sidebar_stack)
        navigation_sidebar_view.add_top_bar(navigation_sidebar_header)
        navigation_sidebar.set_child(navigation_sidebar_view)

        navigation_content_header = Adw.HeaderBar()
        navigation_content_header.set_show_end_title_buttons(False)
        self.navigation_content_view = Adw.ToolbarView()
        self.navigation_content_view.add_top_bar(navigation_content_header)
        self.navigation_content.set_child(self.navigation_content_view)

        self.navigation_content_view.set_content(
            Adw.StatusPage(title="Select an activity")
        )

        self.activities_scroller = Gtk.ScrolledWindow()
        self.activities_list = None
        navigation_sidebar_stack.add_titled(
            self.activities_scroller, "activities", "Activities"
        )

        self.calendar = Gtk.Calendar()
        for signal in ["next-month", "prev-month", "next-year", "prev-year"]:
            self.calendar.connect(signal, self.update_calendar)
        self.calendar.connect("day-selected", self.show_activities_for_day)
        self.calendar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.calendar_box.append(self.calendar)
        navigation_sidebar_stack.add_titled(self.calendar_box, "calendar", "Calendar")

        self.status_page = Adw.StatusPage(title="Waiting for activities to be loaded")
        self.activities_scroller.set_child(self.status_page)

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
        self.add_activities()
        self.update_calendar(None)
        self.show_activities_for_day(None)
        self.application.register_on_sync_func(self.add_activities)
        self.application.register_on_sync_func(lambda: self.update_calendar(None))

    def add_activities(self):
        self.activities_list = Gtk.ListBox()
        self.activities_list.add_css_class("navigation-sidebar")
        self.activities_scroller.set_child(self.activities_list)
        activities = self.application.athlete.activities.sort_index(
            ascending=False
        ).activity

        for activity in activities:
            self.activities_list.append(self.create_activity_row(activity))
        self.activities_list.connect("row-activated", self.display_activity)

    def display_activity(self, _, row):
        activity = row.activity
        details = activity.meta_details
        self.navigation_content.set_title(str(details["activityName"]))
        activity_view = ActivityView.create(activity)
        self.navigation_content_view.set_content(activity_view)

    def update_calendar(self, _):
        self.calendar.clear_marks()
        month = self.calendar.get_date().get_month()
        year = self.calendar.get_date().get_year()
        start = datetime.date(year=year, month=month, day=1)
        if month == 12:
            month = 0
            year += 1
        end = datetime.date(year=year, month=month + 1, day=1)

        self.calendar.activities = self.application.athlete.days.loc[
            self.application.athlete.days.index >= start
        ]
        self.calendar.activities = self.calendar.activities.loc[
            self.calendar.activities.index < end
        ]

        for day in self.calendar.activities.index:
            self.calendar.mark_day(day.day)

    def show_activities_for_day(self, _):
        date = self.calendar.get_date()
        date = datetime.date(*date.get_ymd())

        try:
            self.calendar_box.remove(self.calendar.activities_list)
        except AttributeError:
            pass

        try:
            activities = self.calendar.activities.loc[date, "activities"]
            self.calendar.activities_list = Gtk.ListBox()
            self.calendar.activities_list.add_css_class("navigation-sidebar")
            self.calendar_box.append(self.calendar.activities_list)

            for activity in activities:
                self.calendar.activities_list.append(self.create_activity_row(activity))
            self.calendar.activities_list.connect(
                "row-activated", self.display_activity
            )
        except KeyError:
            logging.debug(f"No activities on {date}")

    @staticmethod
    def create_activity_row(activity: Activity):
        details = activity.meta_details
        name = f"{details['startTimeLocal'].split(' ')[0]}: {details['activityName']}"
        label = Gtk.Label(label=name, ellipsize=Pango.EllipsizeMode.END)
        label.set_xalign(0)
        row = Gtk.ListBoxRow(activatable=True)
        row.set_child(label)
        row.activity = activity
        return row
