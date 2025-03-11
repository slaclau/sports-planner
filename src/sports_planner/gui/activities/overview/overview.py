from typing import TYPE_CHECKING, List
import logging

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GObject, Gtk, Gio, Gdk

from sports_planner.gui.activities.overview.tile import Tile

if TYPE_CHECKING:
    from sports_planner.gui.app import Context

logger = logging.getLogger(__name__)


class Overview(Gtk.ScrolledWindow):
    def __init__(self, name, context: "Context"):
        super().__init__(hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.name = name
        self.context = context
        self.settings = Gio.Settings(
            schema_id="io.github.slaclau.sports-planner.views.activities.tabs.overview",
            path=f"/io/github/slaclau/sports-planner/views/activities/tabs/{name}/",
        )

        self.n_columns = 3
        self.spacing = 16
        self.margin = 24
        self.row_spacing = 16
        self.row_height = 48

        self.set_margin_start(self.margin)
        self.set_margin_end(self.margin)
        self.set_margin_top(self.margin)
        self.set_margin_bottom(self.margin)

        self.tiles = []
        self.grid: Gtk.Grid | None = None
        self.add_content()

    @staticmethod
    def _on_prepare(source, x, y, val):
        value = GObject.Value()
        value.init(Tile)
        value.set_object(val)

        return Gdk.ContentProvider.new_for_value(value)

    @staticmethod
    def _on_drag_begin(source, x, y):
        pass

    @staticmethod
    def _on_drop(target, tile, x, y):
        print("on drop")

        return True

    def add_content(self):
        self.grid = Gtk.Grid(
            column_homogeneous=True,
            row_homogeneous=True,
            column_spacing=self.spacing,
            row_spacing=self.row_spacing,
        )
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(box)
        box.append(self.grid)

        drop_target = Gtk.DropTarget.new(Tile, Gdk.DragAction.MOVE)
        self.add_controller(drop_target)
        drop_target.connect("drop", lambda t, x, y, val: self._on_drop(t, x, y, val))

        for tile_id in self.settings.get_value("tiles").unpack():
            tile = Tile(tile_id, self)
            drop_controller = Gtk.DropControllerMotion()
            drag_source = Gtk.DragSource(
                actions=Gdk.DragAction.MOVE,
            )
            tile.add_controller(drop_controller)
            tile.add_controller(drag_source)
            drag_source.connect("prepare", self._on_prepare, tile)
            drag_source.connect("drag-begin", self._on_drag_begin, tile)

            def _update_func(t):
                self.update_content()
                t.update_size_request()

            tile.settings.connect("changed", lambda t, _: _update_func(t))
            self.tiles.append(tile)
        self.update_content()

    def update_content(self):
        for tile in self.tiles:
            if tile.get_parent() is not None:
                self.grid.remove(tile)

        columns = [[] for _ in range(self.n_columns)]
        current_next_column = 0

        for i in range(0, len(self.tiles)):
            tile = self.tiles[i]
            logger.debug(f"adding tile {tile.id}")
            if i == 0:
                for j in range(current_next_column, current_next_column + tile.columns):
                    columns[j].append(tile)
                attach_args = [current_next_column, 0, tile.columns, tile.height]
                self.grid.attach(tile, *attach_args)
                logger.debug(f"attached at {attach_args}")
                current_next_column = current_next_column + tile.columns
            else:
                if current_next_column + tile.columns > self.n_columns:
                    current_next_column = 0
                    logger.debug("resetting current next column")
                above_tiles = [
                    column[-1]
                    for column in columns[
                        current_next_column : current_next_column + tile.columns
                    ]
                    if len(column) > 0
                ]
                logger.debug(f"above tiles {[tile.id for tile in above_tiles]}")
                positions = [self.grid.query_child(tile) for tile in above_tiles]
                if len(positions) > 0:
                    row = max([position[1] + position[3] for position in positions])
                else:
                    row = 0
                attach_args = [current_next_column, row, tile.columns, tile.height]
                self.grid.attach(tile, *attach_args)
                logger.debug(f"attached at {attach_args}")
                for j in range(current_next_column, current_next_column + tile.columns):
                    columns[j].append(tile)
                current_next_column = current_next_column + tile.columns
