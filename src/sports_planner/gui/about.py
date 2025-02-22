import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk


def show_about(app_id, version, parent):
    developers = ["Sebastien Laclau"]
    designers = ["Sebastien Laclau"]

    about = Adw.AboutDialog(
        application_name="Sports Planner",
        application_icon=app_id,
        developer_name=developers[0],
        developers=developers,
        designers=designers,
        # Translators should localize the following string which
        # will be displayed at the bottom of the about box to give
        # credit to the translator(s).
        version=version,
        website="https://github.com/slaclau/sports-planner/",
        issue_url="https://github.com/slaclau/sports-planner/issues/",
        copyright="© Sebastien Laclau",
        license_type=Gtk.License.GPL_3_0,
    )

    about.present(parent)
