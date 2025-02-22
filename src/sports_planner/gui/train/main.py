import typing

import gi
import libantplus.data.sport

from sports_planner.gui.chart import Gauge, HorizontalGauge
from sports_planner.training.main import Trainer

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, GLib, Gtk


class TrainingView(Gtk.Box):
    __gtype_name__ = "TrainingView"

    def __init__(self) -> None:
        super().__init__()
        self.simulation = True
        self.refresh_period = 100
        button_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        scroller = Gtk.ScrolledWindow()
        scroller.set_child(button_box)
        self.append(scroller)

        group = Adw.PreferencesGroup()
        button_box.append(group)
        self.master_row = Adw.SwitchRow(title="Master")
        self.master_switch = (
            self.master_row.get_child().get_last_child().get_last_child()
        )
        self.master_switch.connect(
            "state-set", lambda _, state: self.on_switch("master", state)
        )
        group.add(self.master_row)

        self.sensor_group = Adw.PreferencesGroup(title="Sensors")
        self.sensor_group.set_sensitive(False)
        button_box.append(self.sensor_group)
        self.hrm_row = Adw.SwitchRow(title="HRM")
        self.hrm_switch = self.hrm_row.get_child().get_last_child().get_last_child()
        self.hrm_switch.connect(
            "state-set", lambda _, state: self.on_switch("hrm", state)
        )
        self.scs_row = Adw.SwitchRow(title="SCS")
        self.scs_switch = self.scs_row.get_child().get_last_child().get_last_child()
        self.scs_switch.connect(
            "state-set", lambda _, state: self.on_switch("scs", state)
        )
        self.pwr_row = Adw.SwitchRow(title="PWR")
        self.pwr_switch = self.pwr_row.get_child().get_last_child().get_last_child()
        self.pwr_switch.connect(
            "state-set", lambda _, state: self.on_switch("pwr", state)
        )
        self.trainer_row = Adw.SwitchRow(title="Trainer")
        self.trainer_switch = (
            self.trainer_row.get_child().get_last_child().get_last_child()
        )
        self.trainer_switch.connect(
            "state-set", lambda _, state: self.on_switch("trainer", state)
        )
        self.fe_row = Adw.SwitchRow(title="Broadcast")
        self.fe_switch = self.fe_row.get_child().get_last_child().get_last_child()
        self.fe_switch.connect(
            "state-set", lambda _, state: self.on_switch("broadcast", state)
        )
        self.bu_row = Adw.SwitchRow(title="Broadcast (brake)")
        self.bu_switch = self.bu_row.get_child().get_last_child().get_last_child()
        self.bu_switch.connect(
            "state-set", lambda _, state: self.on_switch("broadcast_brake", state)
        )
        self.sensor_group.add(self.hrm_row)
        self.sensor_group.add(self.scs_row)
        self.sensor_group.add(self.pwr_row)
        self.sensor_group.add(self.trainer_row)
        self.sensor_group.add(self.fe_row)

        self.simulate_group = Adw.PreferencesGroup(title="Simulated sensors")
        self.simulate_group.set_sensitive(False)
        self.simulate_group.set_visible(self.simulation)
        button_box.append(self.simulate_group)

        self.bu_row = Adw.SwitchRow(title="Broadcast (brake)")
        self.bu_switch = self.bu_row.get_child().get_last_child().get_last_child()
        self.bu_switch.connect(
            "state-set", lambda _, state: self.on_switch("broadcast_brake", state)
        )
        self.simulate_group.add(self.bu_row)

        hr_control = None
        speed_control = None
        power_control = None
        cadence_control = None
        balance_control = None

        def update(_):
            self.trainer.brake_data.heart_rate = hr_control.get_value()
            self.trainer.brake_data.speed = speed_control.get_value()
            self.trainer.brake_data.power = power_control.get_value()
            self.trainer.brake_data.cadence = cadence_control.get_value()
            self.trainer.brake_data.balance = balance_control.get_value()

        hr_control = Adw.SpinRow.new_with_range(50, 250, 1)
        hr_control.set_value(100)
        hr_control.set_title("Heart rate")
        hr_control.get_adjustment().connect("value-changed", update)
        self.simulate_group.add(hr_control)

        speed_control = Adw.SpinRow.new_with_range(0, 100, 0.1)
        speed_control.set_value(20.5)
        speed_control.set_title("Speed")
        speed_control.get_adjustment().connect("value-changed", update)
        self.simulate_group.add(speed_control)

        power_control = Adw.SpinRow.new_with_range(0, 1000, 1)
        power_control.set_value(250)
        power_control.set_title("Power")
        power_control.get_adjustment().connect("value-changed", update)
        self.simulate_group.add(power_control)

        cadence_control = Adw.SpinRow.new_with_range(50, 130, 1)
        cadence_control.set_value(90)
        cadence_control.set_title("Cadence")
        cadence_control.get_adjustment().connect("value-changed", update)
        self.simulate_group.add(cadence_control)

        balance_control = Adw.SpinRow.new_with_range(0, 100, 1)
        balance_control.set_value(49)
        balance_control.set_title("Balance")
        balance_control.get_adjustment().connect("value-changed", update)
        self.simulate_group.add(balance_control)

        self.trainer: typing.Optional[Trainer] = None
        self.source_id: typing.Optional[int] = None

        grid = Gtk.Grid()
        grid.set_row_homogeneous(True)
        grid.set_column_homogeneous(True)
        grid.set_vexpand(True)
        grid.set_hexpand(True)
        grid.set_size_request(500, 600)
        self.append(grid)

        self.hr_gauge = Gauge(begin=50, end=250, title="Heart rate", value_format="d")
        self.speed_gauge = Gauge(begin=0, end=100, title="Speed", value_format=".1f")
        self.cadence_gauge = Gauge(
            begin=50,
            end=130,
            title="Cadence",
            zones=[80, 100],
            zone_colours=["green"],
            ticks=range(50, 140, 10),
            minor_ticks=range(50, 132, 2),
            value_format=".0f",
        )
        self.power_gauge = Gauge(begin=0, end=1000, title="Power", value_format=".0f")
        self.balance_gauge = HorizontalGauge(
            begin=0, end=100, title="Balance", value_format=".0f"
        )

        grid.attach(self.hr_gauge, 0, 0, 1, 1)
        grid.attach(self.speed_gauge, 1, 0, 1, 1)
        grid.attach(self.cadence_gauge, 1, 1, 1, 1)
        grid.attach(self.power_gauge, 0, 1, 1, 1)
        grid.attach(self.balance_gauge, 0, 2, 1, 1)

    def on_switch(self, sensor, state):
        if sensor == "master":
            if state:
                self.on_start(None)
            else:
                self.on_stop(None)
        elif sensor == "broadcast":
            if state:
                self.trainer.broadcast("fe")
            else:
                self.trainer.stop_broadcast("fe")
        elif sensor == "broadcast_brake":
            if state:
                self.trainer.broadcast("bu")
            else:
                self.trainer.stop_broadcast("bu")
        else:
            if state:
                self.trainer.pair(sensor)
            else:
                self.trainer.unpair(sensor)
        return True

    def on_start(self, _):
        if self.source_id is None:
            try:
                self.trainer = Trainer()
                self.source_id = GLib.timeout_add(self.refresh_period, self.gui_update)
                self.sensor_group.set_sensitive(True)
                self.simulate_group.set_sensitive(True)
            except AssertionError:
                self.master_switch.set_active(False)

    def on_stop(self, _):
        for switch in [
            self.hrm_switch,
            self.scs_switch,
            self.pwr_switch,
            self.trainer_switch,
            self.fe_switch,
            self.bu_switch,
        ]:
            switch.set_active(False)
        self.sensor_group.set_sensitive(False)
        self.simulate_group.set_sensitive(False)
        if self.trainer is not None:
            self.trainer.stop()
            self.trainer = None

        self.hr_gauge.set_value(None)
        self.speed_gauge.set_value(None)
        self.cadence_gauge.set_value(None)
        self.power_gauge.set_value(None)

        self.power_gauge.set_value(None, secondary=True)

    def gui_update(self):
        running = False
        hrm_connected = False
        scs_connected = False
        pwr_connected = False
        trainer_connected = False
        broadcasting = False
        bu_broadcasting = False

        if self.master_switch.get_active() and self.trainer is not None:
            running = (
                self.trainer.usb_dongle.handler_thread_active
                and self.trainer.usb_dongle.read_thread_active
            )

        if self.hrm_switch.get_active():
            hrm_connected = self.trainer.hrm_intf.connected
            self.hrm_row.set_subtitle(str(self.trainer.hrm_intf.device_number))
            if self.trainer.hrm_intf.status == self.trainer.hrm_intf.Status.CLOSED:
                self.hrm_switch.set_active(False)
        else:
            self.hrm_row.set_subtitle("")

        if self.scs_switch.get_active():
            scs_connected = self.trainer.scs_intf.connected
            self.scs_row.set_subtitle(str(self.trainer.scs_intf.device_number))
            if self.trainer.scs_intf.status == self.trainer.scs_intf.Status.CLOSED:
                self.scs_switch.set_active(False)
        else:
            self.scs_row.set_subtitle("")

        if self.trainer_switch.get_active():
            trainer_connected = self.trainer.hu_intf.connected
            self.trainer_row.set_subtitle(str(self.trainer.hu_intf.device_number))
            if self.trainer.hu_intf.status == self.trainer.hu_intf.Status.CLOSED:
                self.scs_switch.set_active(False)
        else:
            self.trainer_row.set_subtitle("")

        if self.fe_switch.get_active() and (
            self.trainer.fe_master_intf.status
            == self.trainer.fe_master_intf.Status.OPEN
        ):
            self.fe_row.set_subtitle(str(self.trainer.fe_master_intf.device_number))
            broadcasting = True
        else:
            self.fe_row.set_subtitle("")

        if self.bu_switch.get_active() and (
            self.trainer.bu_master_intf.status
            == self.trainer.bu_master_intf.Status.OPEN
        ):
            self.bu_row.set_subtitle(str(self.trainer.bu_master_intf.device_number))
            bu_broadcasting = True
        else:
            self.bu_row.set_subtitle("")

        self.master_switch.set_state(running)

        self.hrm_switch.set_state(hrm_connected)
        self.scs_switch.set_state(scs_connected)
        self.trainer_switch.set_state(trainer_connected)
        self.fe_switch.set_state(broadcasting)
        self.bu_switch.set_state(bu_broadcasting)

        if trainer_connected:
            if (
                self.trainer.trainer_data.mode
                == libantplus.data.sport.TrainerData.TrainerTargetMode.power
            ):
                self.power_gauge.set_value(
                    self.trainer.trainer_data.target, secondary=True
                )
            else:
                self.power_gauge.set_value(None, secondary=True)
        if hrm_connected:
            hr = self.trainer.data.heart_rate
        elif trainer_connected:
            hr = self.trainer.trainer_data.heart_rate
        else:
            hr = None
        if hr in [0, 255]:
            hr = None

        if scs_connected:
            speed = self.trainer.data.speed
            cadence = self.trainer.data.cadence
        elif trainer_connected:
            speed = self.trainer.trainer_data.speed
            cadence = self.trainer.trainer_data.cadence
        else:
            speed = None
            cadence = None

        if pwr_connected:
            power = self.trainer.data.power
            balance = self.trainer.data.balance
        elif trainer_connected:
            power = self.trainer.trainer_data.power
            balance = self.trainer.trainer_data.balance
        else:
            power = None
            balance = None

        self.hr_gauge.set_value(hr)
        self.speed_gauge.set_value(speed)
        self.cadence_gauge.set_value(cadence)
        self.power_gauge.set_value(power)
        self.balance_gauge.set_value(balance)

        return running


def main(app):
    window = Adw.Window(title="ANT+ Trainer", application=app)
    view = Adw.ToolbarView()
    view.add_top_bar(Adw.HeaderBar())
    window.set_content(view)
    view.set_content(TrainingView())
    window.present()


def standalone():
    app = Adw.Application(application_id="io.github.slaclau.sports_planner.ant_trainer")
    app.connect("activate", main)
    app.run()


if __name__ == "__main__":
    standalone()
