from typing import TYPE_CHECKING, List
import logging

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GObject, Gtk, Gio, Gdk

from sports_planner.gui.activities.overview.tile import Tile

if TYPE_CHECKING:
    from sports_planner.gui.main import Context

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class Overview(Gtk.Widget):
    def __init__(self, name, context: "Context"):
        super().__init__()
        self.name = name
        self.settings = Gio.Settings(
            schema_id="io.github.slaclau.sports-planner.views.activities.tabs.overview",
            path=f"/io/github/slaclau/sports-planner/views/activities/tabs/{name}/",
        )
        self.layout_manager = Gtk.ConstraintLayout()
        self.set_layout_manager(self.layout_manager)

        self.n_columns = 5
        self.spacing = 16
        self.margin = 24
        self.row_spacing = 16
        self.row_height = 16

        self.tiles = []

        self.add_content()

    @staticmethod
    def _on_prepare(source, x, y, val):
        print(f"prepare {source} {x} {y} {val}")
        value = GObject.Value()
        value.init(Tile)
        value.set_object(val)

        return Gdk.ContentProvider.new_for_value(value)
        return Gdk.ContentProvider.new_for_value(source)

    @staticmethod
    def _on_drag_begin(source, x, y):
        print(f"drag begin {source} {x} {y}")

    @staticmethod
    def _on_drop(target, tile, x, y):
        col = int(x * target.get_widget().n_columns / target.get_widget().get_width())
        tile.start_column = col
        tile.settings.set_int("start-column", col)
        target.get_widget().update_start_constraint(tile)

        return True

    def update_start_constraint(self, tile):
        start_multiplier = tile.start_column / self.n_columns
        start_constant = (
                self.margin
                + tile.start_column
                * (self.spacing - 2 * self.margin)
                / self.n_columns
        )
        start_constraint = Gtk.Constraint(
            multiplier=start_multiplier,
            constant=start_constant,
            target=tile,
            target_attribute=Gtk.ConstraintAttribute.START,
            source_attribute=Gtk.ConstraintAttribute.WIDTH,
            relation=Gtk.ConstraintRelation.EQ,
            strength=Gtk.ConstraintStrength.REQUIRED,
        )

        if hasattr(tile, "start_constraint"):
            self.layout_manager.remove_constraint(tile.start_constraint)
        self.layout_manager.add_constraint(start_constraint)
        tile.start_constraint = start_constraint


    def add_content(self):
        drop_target = Gtk.DropTarget.new(Tile, Gdk.DragAction.MOVE)
        self.add_controller(drop_target)
        drop_target.connect("drop", lambda t, x, y, val: self._on_drop(t, x, y, val))

        for tile in self.settings.get_value("tiles").unpack():
            logger.debug(f"adding tile {tile}")
            self.add_tile(tile)
        # Should sort tiles by columns
        self._update_cell_starts()

    def _update_cell_starts(self):
        columns: List[List[Tile]] = [[]] * self.n_columns
        for tile in self.tiles:
            spanned_cols = range(tile.start_column, tile.start_column + tile.columns)
            for col in spanned_cols:
                columns[col] = columns[col] + [tile]
            if hasattr(tile, "start_row"):
                delattr(tile, "start_row")

        for col in columns:
            if len(col) == 0:
                continue
            if not hasattr(col[0], "start_row"):
                col[0].start_row = 0
                constraint = Gtk.Constraint(
                    constant=self.margin,
                    target=col[0],
                    target_attribute=Gtk.ConstraintAttribute.TOP,
                    source_attribute=Gtk.ConstraintAttribute.TOP,
                )
                if hasattr(col[0], "top_constraint"):
                    self.layout_manager.remove_constraint(col[0].top_constraint)
                col[0].top_constraint = constraint
                self.layout_manager.add_constraint(constraint)
                col[0].top_constraint = constraint

            for i in range(1, len(col)):
                if not hasattr(col[i], "start_row"):
                    # does it fit?
                    for j in range(i + 1, len(col)):
                        if hasattr(col[j], "start_row"):
                            if (
                                col[j].start_row
                                < col[i - 1].start_row
                                + col[i - 1].height
                                + col[i].height
                            ):
                                col[i].start_row = col[j].start_row + col[j].height
                                constraint = Gtk.Constraint(
                                    constant=self.row_spacing,
                                    target=col[i],
                                    target_attribute=Gtk.ConstraintAttribute.TOP,
                                    source=col[j],
                                    source_attribute=Gtk.ConstraintAttribute.BOTTOM,
                                    relation=Gtk.ConstraintRelation.GE,
                                )
                                if hasattr(col[i], "top_constraint"):
                                    self.layout_manager.remove_constraint(col[i].top_constraint)
                                col[i].top_constraint = constraint
                                self.layout_manager.add_constraint(constraint)
                                col[i].top_constraint = constraint

                    if not (hasattr(col[i], "start_row")):
                        col[i].start_row = col[i - 1].start_row + col[i - 1].height
                        constraint = Gtk.Constraint(
                            constant=self.row_spacing,
                            target=col[i],
                            target_attribute=Gtk.ConstraintAttribute.TOP,
                            source=col[i - 1],
                            source_attribute=Gtk.ConstraintAttribute.BOTTOM,
                        )
                        self.layout_manager.add_constraint(constraint)
                        if hasattr(col[i], "top_constraint"):
                            self.layout_manager.remove_constraint(col[i].top_constraint)
                        col[i].top_constraint = constraint
                        self.layout_manager.add_constraint(constraint)
                        col[i].top_constraint = constraint

    def add_tile(self, tile: str):
        tile_object = Tile(tile, self)
        drop_controller = Gtk.DropControllerMotion()
        drag_source = Gtk.DragSource(
            actions=Gdk.DragAction.MOVE,
        )
        tile_object.add_controller(drop_controller)
        tile_object.add_controller(drag_source)
        drag_source.connect("prepare", self._on_prepare, tile_object)
        drag_source.connect("drag-begin", self._on_drag_begin, tile_object)

        self.tiles += [tile_object]

        tile_object.set_parent(self)
        self.update_start_constraint(tile_object)

        width_multiplier = tile_object.columns / self.n_columns
        width_constant = (
            tile_object.columns - 1
        ) * self.spacing - tile_object.columns * (
            (self.n_columns - 1) * self.spacing + 2 * self.margin
        ) / self.n_columns
        width_constraint = Gtk.Constraint(
            multiplier=width_multiplier,
            constant=width_constant,
            target=tile_object,
            target_attribute=Gtk.ConstraintAttribute.WIDTH,
            source_attribute=Gtk.ConstraintAttribute.WIDTH,
            relation=Gtk.ConstraintRelation.EQ,
            strength=Gtk.ConstraintStrength.REQUIRED,
        )
        height_constant = (
            tile_object.height * self.row_height
            + (tile_object.height - 1) * self.row_spacing
        )
        height_constraint = Gtk.Constraint(
            constant=height_constant,
            target=tile_object,
            target_attribute=Gtk.ConstraintAttribute.HEIGHT,
            relation=Gtk.ConstraintRelation.EQ,
            strength=Gtk.ConstraintStrength.REQUIRED,
        )
        tile_object.width_constraint = width_constraint
        tile_object.height_constraint = height_constraint

        self.layout_manager.add_constraint(width_constraint)
        self.layout_manager.add_constraint(height_constraint)

        def update_func(tile, _):
            self.update_start_constraint(tile)
            self._update_cell_starts()

        tile_object.connect("notify", update_func)
