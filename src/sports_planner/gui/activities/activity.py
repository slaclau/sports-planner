import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, GObject, Gtk

from sports_planner.gui.activities.tab import ActivityTab


@Gtk.Template(
    resource_path="/io/github/slaclau/sports-planner/gtk/activities/activity-view.ui"
)
class ActivityView(Gtk.Box):
    __gtype_name__ = "ActivityView"

    toolbar_view = Gtk.Template.Child("toolbar-view")
    placeholder = Gtk.Template.Child()
    stack: Gtk.Stack = Gtk.Template.Child()

    settings = Gio.Settings(
        schema_id="io.github.slaclau.sports-planner.views.activities"
    )

    tabs_added = False

    def __init__(self):
        super().__init__()

    def set_context(self, context):
        self.context = context
        self.settings.connect("changed::tabs", self.on_tabs_changed)
        self.on_activity_changed()
        self.context.connect(
            "activity-changed", lambda context: self.on_activity_changed()
        )

    def on_activity_changed(self):
        if self.context.activity is not None and not self.tabs_added:
            self.toolbar_view.set_reveal_top_bars(True)
            self.placeholder.set_visible(False)

            for tab in self.settings.get_value("tabs"):
                page = ActivityTab(name=tab, context=self.context)
                self.stack.add_titled(page, tab, page.title)

            self.settings.connect("changed::tabs", self.on_tabs_changed)
            self.tabs_added = True

    def on_tabs_changed(self, settings, key):
        old_tabs = {
            page.get_name(): page.get_child() for page in self.stack.get_pages()
        }
        new_tabs = {
            tab: (
                old_tabs[tab]
                if tab in old_tabs
                else ActivityTab(name=tab, context=self.context)
            )
            for tab in self.settings.get_value("tabs")
        }

        for _, page in old_tabs.items():
            self.stack.remove(page)

        for name, page in new_tabs.items():
            self.stack.add_titled(page, name, page.title)
