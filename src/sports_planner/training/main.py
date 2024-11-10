import logging
import time
import typing

from libantplus import dongle, interface
from libantplus.data import sport
from libantplus.plus import fe, hrm, scs
from libantplus.tacx import bushido


class Trainer:
    hrm_intf: typing.Optional[interface.AntInterface]
    scs_intf: typing.Optional[interface.AntInterface]
    pwr_intf: typing.Optional[interface.AntInterface]
    hu_intf: typing.Optional[interface.AntInterface]
    fe_master_intf: typing.Optional[interface.AntInterface]
    bu_master_intf: typing.Optional[interface.AntInterface]

    def __init__(self):
        logging.getLogger("libantplus.interface").setLevel(logging.INFO)
        logging.getLogger("libantplus.dongle").setLevel(logging.INFO)
        self.fe_master_device_number = 1
        self.bu_master_device_number = 5

        self.usb_dongle = dongle.USBDongle()
        self.usb_dongle.save_messages_to_file = True
        self.usb_dongle.startup()

        self.data = sport.CyclingData()
        self.trainer_data = sport.TrainerData()
        # hack
        self.data = self.trainer_data

        self.brake_data = sport.TrainerData()
        self.brake_data.simulate(fixed_values=True)

        self.usb_dongle.start_read_thread()
        self.usb_dongle.start_handler_thread()

    def broadcast(self, sensor):
        if sensor == "fe":
            self.fe_master_intf = fe.AntFE(
                master=True, device_number=self.fe_master_device_number
            )
            intf = self.fe_master_intf
            intf.data = self.trainer_data
        elif sensor == "bu":
            self.bu_master_intf = bushido.BushidoBrake(
                device_number=self.bu_master_device_number
            )
            intf = self.bu_master_intf
            intf.data = self.brake_data
        self.usb_dongle.configure_channel(intf)

    def stop_broadcast(self, sensor):
        if sensor == "fe":
            intf = self.fe_master_intf
            self.fe_master_intf = None
        elif sensor == "bu":
            intf = self.bu_master_intf
            self.bu_master_intf = None
        self.usb_dongle.close_and_unassign_channel(intf.channel)

    def pair(self, sensor):
        if sensor == "hrm":
            self.hrm_intf = hrm.AntHRM(master=False)
            intf = self.hrm_intf
        elif sensor == "scs":
            self.scs_intf = scs.AntSCS(master=False)
            intf = self.scs_intf
        elif sensor == "trainer":
            self.hu_intf = bushido.BushidoHeadUnit(master=False)
            intf = self.hu_intf
        intf.channel_search_timeout = 4
        if sensor == "trainer":
            intf.data = self.trainer_data
        else:
            intf.data = self.data
        self.usb_dongle.configure_channel(intf)

    def unpair(self, sensor):
        if sensor == "hrm":
            intf = self.hrm_intf
            self.hrm_intf = None
        elif sensor == "scs":
            intf = self.scs_intf
            self.scs_intf = None
        elif sensor == "trainer":
            intf = self.hu_intf
            self.hu_intf = None
        self.usb_dongle.close_and_unassign_channel(intf.channel)

    def stop(self):
        assert self.usb_dongle.release()
        self.usb_dongle = None


if __name__ == "__main__":
    trainer = Trainer()
    while True:
        time.sleep(2)
        print(f"{trainer.trainer_data.mode}: {trainer.trainer_data.target}")
