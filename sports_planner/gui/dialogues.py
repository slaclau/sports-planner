import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw


class PasswordDialogue(Adw.MessageDialog):
    def __init__(self):
        super().__init__()
        self.set_modal(True)
        self.set_heading("Password Dialogue")
        self.entry = Gtk.Entry()
        self.set_extra_child(self.entry)
        self.set_body("Enter password for Garmin account")
        self.add_response("ok", "_OK")
        self.show()

    def get_password(self):
        return self.entry.get_text()
