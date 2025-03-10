import datetime
import logging

import icalendar

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GtkCal", "0.1")

from gi.repository import Adw, Gtk, GtkCal, ICalGLib, Gdk

logger = logging.getLogger(__name__)


@Gtk.Template(resource_path="/io/github/slaclau/sports-planner/gtk/plan/plan-view.ui")
class PlanView(Gtk.Box):
    __gtype_name__ = "PlanView"

    def __init__(self):
        super().__init__()
        self.month_view = GtkCal.MonthView()
        self.month_view.connect("event-activated", lambda view, event: print())
        self.month_view.set_hexpand(True)
        self.append(self.month_view)

    def set_context(self, context):
        green = Gdk.RGBA()
        green.parse("green")

        GtkCal.add_color_to_css(green)
        self.context = context
        logger.info(
            f"adding {len(self.context.athlete.activities)} activities to plan view"
        )
        for activity in self.context.athlete.activities:
            logger.debug(
                f"adding activity {activity.activity_id} - {activity.name} @ {activity.timestamp}"
            )

            event = icalendar.Event()
            event["summary"] = activity.name
            event["description"] = activity.name

            event.start = activity.timestamp
            event.end = activity.timestamp + datetime.timedelta(
                seconds=activity.total_timer_time
            )
            ical_string = event.to_ical().decode("utf-8")

            gtkcal_event = GtkCal.Event.new(
                ICalGLib.Component.new_from_string(ical_string)
            )
            gtkcal_event.set_color(green)
            self.month_view.add_event(gtkcal_event)
