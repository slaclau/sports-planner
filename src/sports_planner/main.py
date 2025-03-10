#!/usr/bin/env python3

import enum
import importlib.resources
import logging
import os
import pathlib
import sys

from profilehooks import profile
from gi.repository import Gio

from sports_planner.gui.app import SportsPlannerApplication, INSTALL_TYPE

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)


def main():
    resource = None
    install_type = None

    if os.path.isfile(
        "/usr/share/io.github.slaclau.sports-planner/resources.gresource"
    ):
        resource = Gio.resource_load(
            "/usr/share/io.github.slaclau.sports-planner/resources.gresource"
        )
        logger.debug("Loading gresource from /usr/share")
        install_type = INSTALL_TYPE.GLOBAL
    elif os.path.isfile(
        pathlib.Path.home()
        / ".local/share/io.github.slaclau.sports-planner/resources.gresource"
    ):
        resource = Gio.resource_load(
            str(
                pathlib.Path.home()
                / ".local/share/io.github.slaclau.sports-planner/resources.gresource"
            )
        )
        logger.debug("Loading gresource from .local/share")
        install_type = INSTALL_TYPE.LOCAL
    elif os.path.isfile(
        importlib.resources.files("sports_planner").joinpath("data/resources.gresource")
    ):
        resource = Gio.resource_load(
            str(
                importlib.resources.files("sports_planner").joinpath(
                    "data/resources.gresource"
                )
            )
        )
        install_type = INSTALL_TYPE.WHEEL
        logger.debug("Loading gresource from package directory")
    if resource is None:
        logger.warning("No gresource located, unable to determine install type")
        sys.exit(1)
    else:
        Gio.Resource._register(resource)

    app = SportsPlannerApplication(install_type=install_type)
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Found the following resources: {resource.enumerate_children(
                app.get_resource_base_path(), Gio.ResourceLookupFlags.NONE
            )}"
        )
    return app.run(sys.argv)


if __name__ == "__main__":
    main()
