GREEN = 0
YELLOW = 1
RED = 2
BLACK = 3
WHITE = 4
GRAY = 5

GREEN_HEX = 0x66BB6A
YELLOW_HEX = 0xFFEE58
RED_HEX = 0xEF5350
BLACK_HEX = 0x000000
WHITE_HEX = 0xFFFFFF
GRAY_HEX = 0x9E9E9E

BAR_PADDING: int = 5
BAR_HEIGHT: int = 25
ROW_PADDING: int = 5
ROW_HEIGHT: int = BAR_HEIGHT + 2*BAR_PADDING + 2*ROW_PADDING
TEXT_COLUMN_WIDTH: int = 45
OVER_LIMIT_WIDTH: int = 75

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

    def __init__(self, display, tier1_price_centicents, tier2_price_centicents, tier1_limit):
        self.display: FramebufferDisplay = display
        self.tier1_limit: int = tier1_limit

        self.palette = displayio.Palette(6)
        self.palette[BLACK] = BLACK_HEX
        self.palette[GREEN] = GREEN_HEX
        self.palette[YELLOW] = YELLOW_HEX
        self.palette[RED] = RED_HEX
        self.palette[WHITE] = WHITE_HEX
        self.palette[GRAY] = GRAY_HEX

        self.rows = [n*ROW_HEIGHT for n in range(3)]

        self._initialize_display(tier1_price_centicents, tier2_price_centicents)

    def update(self, grid_intensity_g_kwh=0, average_grid_intensity_g_kwh=0, grid_clean_percent=0, energy_usage_kwh=0):
        """Update the dashboard with the latest data."""
        grid_intensity_percentage = grid_intensity_g_kwh/average_grid_intensity_g_kwh * 100
        self.grid_intensity_gauge.width = self._bar_length_by_percent(grid_intensity_percentage)

        intensity_text = self._metric_label(
            text=f"{grid_intensity_g_kwh} gCO2/kWh",
            x=TEXT_COLUMN_WIDTH + ROW_PADDING,
            y=self.rows[0],
        )
        self.display.root_group.append(intensity_text)

        self.grid_clean_share_gauge.width = self._bar_length_by_percent(grid_clean_percent)

        clean_text = self._metric_label(
            text=f"{grid_clean_percent}%",
            x=TEXT_COLUMN_WIDTH + ROW_PADDING,
            y=self.rows[1],
        )
        self.display.root_group.append(clean_text)

        energy_usage_percent = energy_usage_kwh/self.tier1_limit * 100
        self.energy_usage_gauge.width = self._bar_length_by_percent(energy_usage_percent)

    def _initialize_display(self, tier1_price_centicents, tier2_price_centicents):
        rows = self.rows
        full_width = self.display.width
        display_group = displayio.Group()

        # carbon intensity

        self.grid_intensity_gauge = vectorio.Rectangle(
            pixel_shader=self.palette,
            color_index=GRAY,
            width=1,
            height=BAR_HEIGHT,
            x=TEXT_COLUMN_WIDTH,
            y=rows[0] + BAR_PADDING + ROW_PADDING,
        )
        display_group.append(self.grid_intensity_gauge)

        average_tick = self._vertical_line(
            x=full_width - OVER_LIMIT_WIDTH,
            y=rows[0],
        )
        display_group.append(average_tick)

        display_group.append(self._metric_label("Vs Avg", y=rows[0]))

        # grid stress

        self.grid_clean_share_gauge = vectorio.Rectangle(
            pixel_shader=self.palette,
            color_index=GRAY,
            width=1,
            height=BAR_HEIGHT,
            x=TEXT_COLUMN_WIDTH,
            y=rows[1] + BAR_PADDING + ROW_PADDING,
        )
        display_group.append(self.grid_clean_share_gauge)

        capacity_tick = self._vertical_line(
            x=full_width - OVER_LIMIT_WIDTH,
            y=rows[1],
        )
        display_group.append(capacity_tick)

        display_group.append(self._metric_label("Clean %", y=rows[1]))

        # price

        self.energy_usage_gauge = vectorio.Rectangle(
            pixel_shader=self.palette,
            color_index=GRAY,
            width=1,
            height=BAR_HEIGHT,
            x=TEXT_COLUMN_WIDTH,
            y=rows[2] + BAR_PADDING + ROW_PADDING,
        )
        display_group.append(self.energy_usage_gauge)

        tier1_limit_tick = self._vertical_line(
            x=full_width - OVER_LIMIT_WIDTH,
            y=rows[2],
        )
        display_group.append(tier1_limit_tick)

        display_group.append(self._metric_label("Price", y=rows[2]))

        self.display.root_group = display_group

    def _price_label_text(self, price_centicents):
        """Return a string representation of the price in cents per kWh."""
        return f"{price_centicents/100:.2f} $/kWh"

    def _bar_length_by_percent(self, percentage):
        """Return the length of the bar in pixels given a percentage."""
        theoretical = int((self.display.width - TEXT_COLUMN_WIDTH - OVER_LIMIT_WIDTH) * percentage/100)

        return max(1, theoretical)

    def _vertical_line(self, x, y, color=WHITE):
        """Return a vertical line at the given x coordinate."""
        return vectorio.Rectangle(
            pixel_shader=self.palette,
            color_index=color,
            width=1,
            height=ROW_HEIGHT - ROW_PADDING,
            x=x,
            y=y + ROW_PADDING,
        )

    def _metric_label(self, text, x=0, y=0, anchor_point=(0, 0.5)):
        """Return a label for a metric."""
        return Label(
            terminalio.FONT,
            text=text,
            color=WHITE_HEX,
            anchored_position=(x, y + ROW_HEIGHT//2),
            anchor_point=anchor_point,
        )
