from math import floor
from typing import TYPE_CHECKING, List
import logging

import gi
from docutils.utils import column_width

gi.require_version("Gtk", "4.0")
from gi.repository import GObject, Gtk, Gio, Gdk, GLib

from sports_planner.gui.activities.overview.tile import Tile

if TYPE_CHECKING:
    from sports_planner.gui.app import Context

logger = logging.getLogger(__name__)


class Overview(Gtk.ScrolledWindow):
    def __init__(self, name, context: "Context"):
        super().__init__()
        self.set_child(_Overview(name, context))


class _Overview(Gtk.Widget):
    def __init__(self, name, context: "Context"):
        super().__init__()
        self.name = name
        self.context = context
        self.settings = Gio.Settings(
            schema_id="io.github.slaclau.sports-planner.views.activities.tabs.overview",
            path=f"/io/github/slaclau/sports-planner/views/activities/tabs/{name}/",
        )

        self.n_columns = 4
        self.spacing = 16
        self.margin = 24
        self.row_spacing = 16
        self.row_height = 16

        self.set_margin_start(self.margin)
        self.set_margin_end(self.margin)
        self.set_margin_top(self.margin)
        self.set_margin_bottom(self.margin)

        drop_target = Gtk.DropTarget.new(Tile, Gdk.DragAction.MOVE)
        drop_target.connect("drop", self._on_drop)
        self.add_controller(drop_target)

        click_controller = Gtk.GestureClick()
        click_controller.set_button(3)
        click_controller.connect("pressed", self._on_click)
        self.add_controller(click_controller)

        self.tiles = []
        self.tile_ids = self.settings.get_value("tiles").unpack()
        logger.debug(f"got tiles {self.tile_ids}")

        self._add_tiles()

    def _add_tiles(self):
        self.settings.set_value("tiles", GLib.Variant("aas", self.tile_ids))
        for column in self.tiles:
            for tile in column:
                tile.unparent()
        self.tiles = []
        for column in self.tile_ids:
            tiles = []
            for tile_id in column:
                tile = Tile(tile_id, self)
                drop_controller = Gtk.DropControllerMotion()
                drag_source = Gtk.DragSource(
                    actions=Gdk.DragAction.MOVE,
                )
                drag_source.connect("prepare", self._on_prepare, tile)
                drag_source.connect("drag-begin", self._on_drag_begin, tile)

                tile.add_controller(drop_controller)
                tile.add_controller(drag_source)

                tile.settings.connect("changed::type", lambda _, __: self._add_tiles())
                tile.connect("notify", lambda _, __: self.queue_allocate())

                def remove(_tile):
                    for column in self.tile_ids:
                        try:
                            column.remove(_tile.id)
                            break
                        except ValueError:
                            pass
                    self._add_tiles()

                tile.connect("removed", lambda t: remove(t))
                tiles.append(tile)
                tile.set_parent(self)
            self.tiles.append(tiles)

    @staticmethod
    def _on_prepare(source, x, y, val):
        value = GObject.Value()
        value.init(Tile)
        value.set_object(val)

        return Gdk.ContentProvider.new_for_value(value)

    @staticmethod
    def _on_drag_begin(source, drag, widget):
        paintable = Gtk.WidgetPaintable(widget=widget)
        source.set_icon(paintable, 0, 0)

    def _on_click(self, gesture, n_press, x, y):
        column_width = (
            self.get_width() - 2 * self.margin - (self.n_columns - 1) * self.spacing
        ) / self.n_columns

        column = floor((x - self.margin) / column_width)
        column = max(0, column)
        column = min(column, self.n_columns)

        uuid = GLib.uuid_string_random()
        self.tile_ids[column].append(uuid)
        self._add_tiles()

    def _on_drop(self, target, moved_tile, x, y):
        for column in self.tile_ids:
            try:
                column.remove(moved_tile.id)
            except ValueError:
                pass
        column_width = (
            self.get_width() - 2 * self.margin - (self.n_columns - 1) * self.spacing
        ) / self.n_columns

        column = floor((x - self.margin) / column_width)
        column = max(0, column)
        column = min(column, self.n_columns)

        for tile in self.tiles[column]:
            _, bounds = tile.compute_bounds(self)
            if y < bounds.get_y() + bounds.get_height():
                before_id = tile.id
                before_index = self.tile_ids[column].index(before_id)
                self.tile_ids[column].insert(before_index, moved_tile.id)
                self._add_tiles()
                return True
        self.tile_ids[column].append(moved_tile.id)
        self._add_tiles()
        return True

    def do_size_allocate(self, width, height, baseline):
        logger.debug("size allocate")
        column_width = (
            width - 2 * self.margin - (self.n_columns - 1) * self.spacing
        ) / self.n_columns

        column_overflows = [[] for _ in range(0, self.n_columns)]

        x = self.margin
        for i in range(0, len(self.tiles)):
            column = self.tiles[i]
            y = self.margin

            for tile in column:
                tile_allocation = Gdk.Rectangle()
                height = tile.height * self.row_height
                top = height + y
                logger.debug(f"checking for overflow in {i}")
                for widget in column_overflows[i]:
                    logger.debug(f"got {widget}")
                    fits, bounds = widget.compute_bounds(self)
                    assert fits
                    if bounds.get_y() > top:
                        break
                    y = bounds.get_y() + bounds.get_height() + self.row_spacing

                tile_allocation.x = x
                tile_allocation.y = y
                width = tile.columns * column_width + (tile.columns - 1) * self.spacing
                tile_allocation.width = width

                tile_allocation.height = height
                tile.size_allocate(tile_allocation, baseline)

                if tile.columns > 1:
                    logger.debug(
                        f"{tile} overflows into columns {i + 1} - {i + tile.columns - 1}"
                    )
                    for j in range(i + 1, i + tile.columns):
                        column_overflows[j].append(tile)

                y = y + height + self.row_spacing
            x = x + column_width + self.spacing
