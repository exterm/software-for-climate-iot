GREEN = 1
YELLOW = 2
RED = 3
BLACK = 0
WHITE = 4

BLACK_HEX = 0x000000
GREEN_HEX = 0x66BB6A
YELLOW_HEX = 0xFFEE58
RED_HEX = 0xEF5350
WHITE_HEX = 0xFFFFFF

BAR_PADDING: int = 5
BAR_HEIGHT: int = 25
ROW_PADDING: int = 5
ROW_HEIGHT: int = BAR_HEIGHT + 2*BAR_PADDING + 2*ROW_PADDING
TEXT_COLUMN_WIDTH: int = 45

from framebufferio import FramebufferDisplay
import vectorio
import displayio
from adafruit_display_text.bitmap_label import Label
import terminalio

class Dashboard:
    """
    Display a personalized power supply dashboard from precomputed values.

    We'll display three horizontal gauges, one for each of the following:
    - current grid carbon intensity
    - current grid stress factor (calculated as a function of capacity and demand)
    - current energy price per kWh based on tiered pricing and cumulative usage
    """

    def __init__(self, display):
        self.display: FramebufferDisplay = display

        palette = displayio.Palette(5)
        palette[BLACK] = BLACK_HEX
        palette[GREEN] = GREEN_HEX
        palette[YELLOW] = YELLOW_HEX
        palette[RED] = RED_HEX
        palette[WHITE] = WHITE_HEX

        rows = [n*ROW_HEIGHT for n in range(3)]

        self.grid_intensity_gauge = vectorio.Rectangle(
            pixel_shader=palette,
            width=display.width,
            height=BAR_HEIGHT,
            x=TEXT_COLUMN_WIDTH,
            y=rows[0] + BAR_PADDING + ROW_PADDING,
        )

        grid_intensity_label = Label(
            terminalio.FONT,
            text="CO2",
            color=WHITE_HEX,
            x=0,
            y=rows[0] + ROW_HEIGHT//2,
            anchor_point=(0, 0.5),
        )

        # next row

        self.grid_stress_gauge = vectorio.Rectangle(
            pixel_shader=palette,
            width=display.width,
            height=BAR_HEIGHT,
            x=TEXT_COLUMN_WIDTH,
            y=rows[1] + BAR_PADDING + ROW_PADDING,
        )

        grid_stress_label = Label(
            terminalio.FONT,
            text="Stress",
            color=WHITE_HEX,
            x=0,
            y=rows[1] + ROW_HEIGHT//2,
            anchor_point=(0, 0.5),
        )

        # next row

        self.energy_price_gauge = vectorio.Rectangle(
            pixel_shader=palette,
            width=display.width,
            height=BAR_HEIGHT,
            x=TEXT_COLUMN_WIDTH,
            y=rows[2] + BAR_PADDING + ROW_PADDING,
        )

        energy_price_label = Label(
            terminalio.FONT,
            text="Price",
            color=WHITE_HEX,
            x=0,
            y=rows[2] + ROW_HEIGHT//2,
            anchor_point=(0, 0.5),
        )

        group = displayio.Group()
        group.append(self.grid_intensity_gauge)
        group.append(grid_intensity_label)
        group.append(self.grid_stress_gauge)
        group.append(grid_stress_label)
        group.append(self.energy_price_gauge)
        group.append(energy_price_label)

        display.root_group = group

    def update(self, grid_intensity, grid_stress, energy_price):
        """Update the dashboard with the latest data."""
        self.grid_intensity_gauge.color_index = self._get_fill_color(grid_intensity)
        self.grid_stress_gauge.color_index = self._get_fill_color(grid_stress)
        self.energy_price_gauge.color_index = self._get_fill_color(energy_price)

    def _get_fill_color(self, value):
        """Return a color based on the value."""
        if value < 0.5:
            return GREEN
        elif value < 0.75:
            return YELLOW
        else:
            return RED

