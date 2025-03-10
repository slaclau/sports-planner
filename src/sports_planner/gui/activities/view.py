import logging

import gi
import sports_planner_lib.utils.format
from profilehooks import profile
from sports_planner_lib.db.schemas import Activity

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, GObject, Gtk

from sports_planner.gui.activities.activity import ActivityView
from sports_planner.gui.activities.calendar import Calendar


class ActivityListItem(GObject.GObject):
    def __init__(self, athlete, activity: "Activity"):
        super().__init__()
        self.athlete = athlete
        self.activity = activity

    @GObject.Property(type=str)
    def label(self):
        return f"{self.activity.timestamp.date()}: {self.activity.name}"

    @GObject.Property(type=str)
    def score(self):
        return f"USS: {self.athlete.get_metric(self.activity, "UniversalStressScore"):0.1f}"

    @GObject.Property(type=str)
    def duration(self):
        return sports_planner_lib.utils.format.time(self.activity.total_timer_time)


logger = logging.getLogger(__name__)


@Gtk.Template(
    resource_path="/io/github/slaclau/sports-planner/gtk/activities/activities-view.ui"
)
class ActivitiesView(Gtk.Box):
    __gtype_name__ = "ActivitiesView"

    calendar_expander = Gtk.Template.Child("calendar-expander")
    activities_expander = Gtk.Template.Child("activities-expander")
    intervals_expander = Gtk.Template.Child("intervals-expander")

    open_calender_button = Gtk.Template.Child("open-calendar-button")
    open_activities_button = Gtk.Template.Child("open-activities-button")
    open_intervals_button = Gtk.Template.Child("open-intervals-button")

    activities_list = Gtk.Template.Child("activities-list")
    activity_pane = Gtk.Template.Child("activity-pane")
    activity_view = Gtk.Template.Child("activity-view")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.open_calender_button.connect(
            "clicked",
            lambda _: self.calendar_expander.set_expanded(
                not self.calendar_expander.get_expanded()
            ),
        )
        self.open_activities_button.connect(
            "clicked",
            lambda _: self.activities_expander.set_expanded(
                not self.activities_expander.get_expanded()
            ),
        )
        self.open_intervals_button.connect(
            "clicked",
            lambda _: self.intervals_expander.set_expanded(
                not self.intervals_expander.get_expanded()
            ),
        )

        add_tab_action = Gio.SimpleAction(name="add-tab")
        add_tab_action.connect("activate", lambda act, _: self._add_tab())
        action_group = Gio.SimpleActionGroup()
        action_group.add_action(add_tab_action)
        self.insert_action_group("activities-view", action_group)

    def _add_tab(self):
        dialog = TabCreationDialog()
        dialog.present(self)

    def set_context(self, context):
        self.context = context

        model = Gio.ListStore(item_type=ActivityListItem)
        for activity in self.context.athlete.activities:
            model.insert(0, ActivityListItem(self.context.athlete, activity))

        selection = Gtk.SingleSelection.new(model)

        factory = Gtk.BuilderListItemFactory.new_from_resource(
            None,
            "/io/github/slaclau/sports-planner/gtk/activities/activity-list-item.ui",
        )

        self.activities_list.set_model(selection)
        self.activities_list.set_factory(factory)

        self.activities_list.connect(
            "activate",
            lambda _, item: self.display_activity(model.get_item(item).activity),
        )

        self.activity_view.set_context(context)

    @profile(filename="display_activity.prof")
    def display_activity(self, activity: "Activity") -> None:
        self.activity_pane.set_title(str(activity.name))

        self.context.activity = activity
        logger.debug(f"Displaying activity {activity}")


@Gtk.Template(
    resource_path="/io/github/slaclau/sports-planner/gtk/activities/tab-creation-dialog.ui"
)
class TabCreationDialog(Adw.Dialog):
    __gtype_name__ = "TabCreationDialog"

    stack: Gtk.Stack = Gtk.Template.Child("stack")

    def __init__(self):
        super().__init__(title="Add a tab")
        add_tab_action = Gio.SimpleAction(
            name="add-tab", parameter_type=GLib.VariantType("s")
        )

        def add_tab_cb(type):
            self.stack.set_visible_child_name(type)
            self.set_title(self.stack.get_visible_child().get_title())

        add_tab_action.connect(
            "activate",
            lambda act, target: add_tab_cb(target.unpack()),
        )
        action_group = Gio.SimpleActionGroup()
        action_group.add_action(add_tab_action)
        self.insert_action_group("add-tab-dialog", action_group)
