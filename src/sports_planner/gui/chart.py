import math

import gi
import numpy as np

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("WebKit", "6.0")
from gi.repository import Adw, Gdk, Gtk, Pango, PangoCairo  # noqa: E402


class Gauge(Gtk.DrawingArea):
    def __init__(self, **kwargs):
        super().__init__()
        self.inner_scale = 0.6
        self.outer_scale = 0.8
        self.begin_angle = 5 / 6 * math.pi
        self.end_angle = 1 / 6 * math.pi

        self.needle_scale = 0.1
        self.secondary_needle_scale = 0.05
        self.needle_fill = True
        self.secondary_needle_fill = False

        self.ticks = None
        self.tick_format = ".0f"
        self.tick_scale = 0.7

        self.minor_ticks = None
        self.minor_tick_scale = 0.75

        self.begin = 0
        self.end = 100

        self.value = None
        self.value_format = ".2f"

        self.secondary_value = None

        self.zones = None
        self.zone_colours = None

        self.title = None
        self.unit = ""

        assert set(kwargs.keys()) <= set(self.__dict__.keys())
        self.__dict__.update((key, value) for key, value in kwargs.items())

        self.set_draw_func(self.on_draw)

    def on_draw(self, circle, context, x, y):
        size = min(
            circle.get_size(Gtk.Orientation.VERTICAL),
            circle.get_size(Gtk.Orientation.HORIZONTAL),
        )
        context.translate(size / 2, size / 2)

        if self.zones is not None and self.zone_colours is not None:
            self.draw_zones(context, size)

        color = self.get_style_context().lookup_color("theme_fg_color")
        rgba = color[1]
        context.set_source_rgb(rgba.red, rgba.green, rgba.blue)
        context.arc_negative(
            0, 0, self.inner_scale * size / 2, self.end_angle, self.begin_angle
        )
        context.arc(0, 0, self.outer_scale * size / 2, self.begin_angle, self.end_angle)
        context.close_path()
        context.stroke()

        if self.value is not None:
            self.draw_pointer(context, size)
            self.draw_value(context, size)

        if self.secondary_value is not None:
            self.draw_pointer(context, size, secondary=True)

        self.draw_ticks(context, size)
        self.draw_ticks(context, size, minor=True)

        self.draw_title(context, size)

        return False

    def draw_zones(self, context, size):
        assert len(self.zones) == len(self.zone_colours) + 1
        zones = np.array(self.zones)
        zone_angles = (zones - self.begin) / (self.end - self.begin) * (
            2 * math.pi - (self.begin_angle - self.end_angle)
        ) + self.begin_angle

        for i in range(0, len(self.zone_colours)):
            context.new_path()
            rgba = Gdk.RGBA()
            if rgba.parse(self.zone_colours[i]):
                context.set_source_rgb(rgba.red, rgba.green, rgba.blue)
            context.arc(
                0, 0, self.inner_scale * size / 2, zone_angles[i], zone_angles[i + 1]
            )
            context.arc_negative(
                0, 0, self.outer_scale * size / 2, zone_angles[i + 1], zone_angles[i]
            )
            context.close_path()
            context.fill()

    def draw_title(self, context, size):
        layout = PangoCairo.create_layout(context)
        font_description = self.get_pango_context().get_font_description()
        font_description.set_size(20 * Pango.SCALE)
        font_description.set_weight(Pango.Weight.BOLD)

        layout.set_font_description(font_description)
        layout.set_alignment(Pango.Alignment.CENTER)
        layout.set_text(self.title)
        layout_size = layout.get_pixel_size()
        context.move_to(-layout_size[0] / 2, 2 * layout_size[1])

        PangoCairo.show_layout(context, layout)

    def draw_value(self, context, size):
        layout = PangoCairo.create_layout(context)
        font_description = self.get_pango_context().get_font_description()
        font_description.set_size(20 * Pango.SCALE)
        font_description.set_weight(Pango.Weight.BOLD)

        layout.set_font_description(font_description)
        layout.set_alignment(Pango.Alignment.CENTER)
        layout.set_text(f"{self.value:{self.value_format}}")
        layout_size = layout.get_pixel_size()
        context.move_to(-layout_size[0] / 2, layout_size[1])

        PangoCairo.show_layout(context, layout)

    def draw_pointer(self, context, size, secondary=False):
        context.new_path()
        if secondary:
            color = self.get_style_context().lookup_color("theme_fg_color")
        else:
            color = self.get_style_context().lookup_color("accent_color")
        rgba = color[1]
        context.set_source_rgb(rgba.red, rgba.green, rgba.blue)
        if secondary:
            value = max(self.begin, self.secondary_value)
            value = min(value, self.end)
            scale = self.secondary_needle_scale
        else:
            value = max(self.begin, self.value)
            value = min(value, self.end)
            scale = self.needle_scale
        angle = (value - self.begin) / (self.end - self.begin) * (
            2 * math.pi - (self.begin_angle - self.end_angle)
        ) + self.begin_angle
        adjust_angle = math.asin(2 * scale / (self.outer_scale + self.inner_scale))
        context.arc(
            0,
            0,
            scale * size / 2,
            angle + math.pi / 2 - adjust_angle,
            angle - math.pi / 2 + adjust_angle,
        )
        x = (self.outer_scale + self.inner_scale) * size / 4 * math.cos(angle)
        y = (self.outer_scale + self.inner_scale) * size / 4 * math.sin(angle)
        context.line_to(x, y)
        context.close_path()
        needle_fill = self.secondary_needle_fill if secondary else self.needle_fill
        if needle_fill:
            context.fill()
        else:
            context.stroke()

    def draw_ticks(self, context, size, minor=False):
        context.new_path()
        color = self.get_style_context().lookup_color("accent_fg_color")
        rgba = color[1]
        context.set_source_rgb(rgba.red, rgba.green, rgba.blue)
        if minor:
            if self.minor_ticks is None:
                ticks = np.arange(
                    self.begin, self.end + 1, (self.end - self.begin) / 50
                )
            else:
                ticks = np.array(self.minor_ticks)
        else:
            if self.ticks is None:
                ticks = np.arange(
                    self.begin, self.end + 1, (self.end - self.begin) / 10
                )
            else:
                ticks = np.array(self.ticks)
        tick_angles = (ticks - self.begin) / (self.end - self.begin) * (
            2 * math.pi - (self.begin_angle - self.end_angle)
        ) + self.begin_angle

        tick_x = np.cos(tick_angles)
        tick_y = np.sin(tick_angles)

        if minor:
            tick_scale = self.minor_tick_scale
        else:
            tick_scale = self.tick_scale
            layout = PangoCairo.create_layout(context)
            font_description = self.get_pango_context().get_font_description()
            layout.set_font_description(font_description)
            layout.set_alignment(Pango.Alignment.CENTER)
        for x, y, tick, angle in zip(tick_x, tick_y, ticks, tick_angles):
            context.move_to(tick_scale * size / 2 * x, tick_scale * size / 2 * y)
            context.line_to(
                self.outer_scale * size / 2 * x, self.outer_scale * size / 2 * y
            )
            if not minor:
                context.rotate(angle + math.pi / 2)
                layout.set_text(f"{tick:{self.tick_format}}")
                layout_size = layout.get_pixel_size()
                context.rel_move_to(-layout_size[0] / 2, -layout_size[1])
                context.save()
                PangoCairo.show_layout(context, layout)
                context.rotate(-angle - math.pi / 2)
            context.stroke()

    def set_value(self, value, secondary=False):
        if secondary:
            self.secondary_value = value
        else:
            self.value = value
        self.queue_draw()


class HorizontalGauge(Gtk.DrawingArea):
    def __init__(self, **kwargs):
        super().__init__()
        self.width = 0.8
        self.height = 0.2
        self.needle_scale = 0.1
        self.secondary_needle_scale = 0.05
        self.needle_fill = True
        self.secondary_needle_fill = False

        self.ticks = None
        self.tick_format = ".0f"
        self.tick_scale = 0.2

        self.minor_ticks = None
        self.minor_tick_scale = 0.1

        self.begin = 0
        self.end = 100

        self.value = None
        self.value_format = ".2f"

        self.secondary_value = None

        self.zones = None
        self.zone_colours = None

        self.title = None
        self.unit = ""

        assert set(kwargs.keys()) <= set(self.__dict__.keys())
        self.__dict__.update((key, value) for key, value in kwargs.items())

        self.set_draw_func(self.on_draw)

    def on_draw(self, bar, context, x, y):
        size = min(
            bar.get_size(Gtk.Orientation.VERTICAL),
            bar.get_size(Gtk.Orientation.HORIZONTAL),
        )
        context.translate(size / 2, size / 2)

        if self.zones is not None and self.zone_colours is not None:
            self.draw_zones(context, size)

        color = self.get_style_context().lookup_color("theme_fg_color")
        rgba = color[1]
        context.set_source_rgb(rgba.red, rgba.green, rgba.blue)
        context.rectangle(
            -self.width * size / 2,
            -self.height * size / 2,
            self.width * size,
            self.height * size,
        )
        context.stroke()

        if self.value is not None:
            self.draw_pointer(context, size)
            self.draw_value(context, size)

        if self.secondary_value is not None:
            self.draw_pointer(context, size, secondary=True)

        self.draw_ticks(context, size)
        self.draw_ticks(context, size, minor=True)

        self.draw_title(context, size)

        return False

    def draw_zones(self, context, size):
        assert len(self.zones) == len(self.zone_colours) + 1
        zones = np.array(self.zones)
        zone_pos = (zones - self.begin) / (self.end - self.begin) * (
            self.width * size
        ) - self.width * size / 2

        for i in range(0, len(self.zone_colours)):
            rgba = Gdk.RGBA()
            if rgba.parse(self.zone_colours[i]):
                context.set_source_rgb(rgba.red, rgba.green, rgba.blue)
            context.rectangle(
                zone_pos[i],
                -self.height * size / 2,
                zone_pos[i + 1] - zone_pos[i],
                self.height * size,
            )
            context.fill()

    def draw_title(self, context, size):
        layout = PangoCairo.create_layout(context)
        font_description = self.get_pango_context().get_font_description()
        font_description.set_size(20 * Pango.SCALE)
        font_description.set_weight(Pango.Weight.BOLD)

        layout.set_font_description(font_description)
        layout.set_alignment(Pango.Alignment.CENTER)
        layout.set_text(self.title)
        layout_size = layout.get_pixel_size()
        context.move_to(-layout_size[0] / 2, -2.5 * layout_size[1])

        PangoCairo.show_layout(context, layout)

    def draw_value(self, context, size):
        layout = PangoCairo.create_layout(context)
        font_description = self.get_pango_context().get_font_description()
        font_description.set_size(20 * Pango.SCALE)
        font_description.set_weight(Pango.Weight.BOLD)

        layout.set_font_description(font_description)
        layout.set_alignment(Pango.Alignment.CENTER)
        layout.set_text(f"{self.value:{self.value_format}}")
        layout_size = layout.get_pixel_size()
        context.move_to(-layout_size[0] / 2, layout_size[1])

        PangoCairo.show_layout(context, layout)

    def draw_pointer(self, context, size, secondary=False):
        context.new_path()
        if secondary:
            color = self.get_style_context().lookup_color("theme_fg_color")
        else:
            color = self.get_style_context().lookup_color("accent_color")
        rgba = color[1]
        context.set_source_rgb(rgba.red, rgba.green, rgba.blue)
        if secondary:
            value = max(self.begin, self.secondary_value)
            value = min(value, self.end)
            scale = self.secondary_needle_scale
        else:
            value = max(self.begin, self.value)
            value = min(value, self.end)
            scale = self.needle_scale
        pos = (value - self.begin) / (self.end - self.begin) * (
            self.width * size
        ) - self.width * size / 2
        context.move_to(pos, self.tick_scale * size / 2 - self.height * size / 2)
        context.rel_line_to(
            scale * size / 2, self.height * size - self.tick_scale * size / 2
        )
        context.rel_line_to(-scale * size, 0)
        context.close_path()
        needle_fill = self.secondary_needle_fill if secondary else self.needle_fill
        if needle_fill:
            context.fill()
        else:
            context.stroke()

    def draw_ticks(self, context, size, minor=False):
        context.new_path()
        color = self.get_style_context().lookup_color("accent_fg_color")
        rgba = color[1]
        context.set_source_rgb(rgba.red, rgba.green, rgba.blue)
        if minor:
            if self.minor_ticks is None:
                ticks = np.arange(
                    self.begin, self.end + 1, (self.end - self.begin) / 25
                )
            else:
                ticks = np.array(self.minor_ticks)
        else:
            if self.ticks is None:
                ticks = np.arange(self.begin, self.end + 1, (self.end - self.begin) / 5)
            else:
                ticks = np.array(self.ticks)
        tick_pos = (ticks - self.begin) / (self.end - self.begin) * (
            self.width * size
        ) - self.width * size / 2

        if minor:
            tick_scale = self.minor_tick_scale
        else:
            tick_scale = self.tick_scale
            layout = PangoCairo.create_layout(context)
            font_description = self.get_pango_context().get_font_description()
            layout.set_font_description(font_description)
            layout.set_alignment(Pango.Alignment.CENTER)
        for pos, tick in zip(tick_pos, ticks):
            context.move_to(pos, -self.height * size / 2)
            context.rel_line_to(0, tick_scale * size / 2)
            context.move_to(pos, -self.height * size / 2)

            if not minor:
                layout.set_text(f"{tick:{self.tick_format}}")
                layout_size = layout.get_pixel_size()
                context.rel_move_to(-layout_size[0] / 2, -layout_size[1])
                context.save()
                PangoCairo.show_layout(context, layout)
            context.stroke()

    def set_value(self, value, secondary=False):
        if secondary:
            self.secondary_value = value
        else:
            self.value = value
        self.queue_draw()


def main(app):
    window = Adw.Window(application=app)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    gauge = Gauge(title="Test", zones=[0, 10], zone_colours=["red"])
    hgauge = HorizontalGauge(title="Test", zones=[0, 10], zone_colours=["red"])

    gauge.set_vexpand(True)
    hgauge.set_vexpand(True)

    slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
    slider.connect("value-changed", lambda scale: gauge.set_value(scale.get_value()))
    slider.connect("value-changed", lambda scale: hgauge.set_value(scale.get_value()))

    box.append(gauge)
    box.append(slider)
    box.append(hgauge)

    gauge.set_value(5, secondary=True)
    hgauge.set_value(5, secondary=True)

    window.set_content(box)
    window.present()


if __name__ == "__main__":
    app = Adw.Application()
    app.connect("activate", main)
    app.run()
