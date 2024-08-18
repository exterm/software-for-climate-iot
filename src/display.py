from framebufferio import FramebufferDisplay
import vectorio
import displayio
from adafruit_display_text.bitmap_label import Label
import terminalio
import math


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
ROW_HEIGHT: int = BAR_HEIGHT + 2 * BAR_PADDING + 2 * ROW_PADDING
TEXT_COLUMN_WIDTH: int = 45
OVER_LIMIT_WIDTH: int = 75

class Dashboard:
    """
    Display a personalized power supply dashboard from precomputed values.

    We'll display three horizontal gauges, one for each of the following:
    - current grid carbon intensity
    - current grid stress factor (calculated as a function of capacity and demand)
    - current energy price per kWh based on tiered pricing and cumulative usage
    """

    def __init__(self, display: FramebufferDisplay, tier1_price_centicents, tier2_price_centicents, tier1_limit):
        self.tier1_limit: int = tier1_limit

        palette = displayio.Palette(6)
        palette[BLACK] = BLACK_HEX
        palette[GREEN] = GREEN_HEX
        palette[YELLOW] = YELLOW_HEX
        palette[RED] = RED_HEX
        palette[WHITE] = WHITE_HEX
        palette[GRAY] = GRAY_HEX

        rows = [n * ROW_HEIGHT for n in range(3)]

        full_width = display.width
        display_group = displayio.Group()
        display.root_group = display_group

        # carbon intensity

        self.grid_intensity_gauge = VsAverageGauge(
            "Carbon",
            full_width,
            display_group,
            palette,
            rows[0],
        )

        # grid stress

        self.demand_gauge = VsAverageGauge(
            "Demand",
            full_width,
            display_group,
            palette,
            rows[1],
        )

        # price

        self.energy_usage_gauge = ExceedableLimitGauge(
            "Price",
            full_width,
            display_group,
            palette,
            rows[2],
            left_label=self._price_label_text(tier1_price_centicents),
            right_label=self._price_label_text(tier2_price_centicents),
        )

    def _price_label_text(self, price_centicents):
        """Return a string representation of the price in cents per kWh."""
        return f"{price_centicents/100:.2f} $/kWh"

    def update(
        self,
        carbon_intensity_history: list[int] = [],
        power_consumption_history: list[int] = [],
        energy_usage_kwh=0,
    ):
        """Update the dashboard with the latest data."""
        self.grid_intensity_gauge.update_from_history(carbon_intensity_history)

        self.demand_gauge.update_from_history(power_consumption_history)

        self.energy_usage_gauge.update(energy_usage_kwh, self.tier1_limit)


class ExceedableLimitGauge:
    def __init__(
        self,
        name: str,
        full_width: int,
        display_group: displayio.Group,
        palette: displayio.Palette,
        y_offset: int,
        left_label: str | None = None,
        right_label: str | None = None,
    ) -> None:
        self.full_width = full_width
        self.palette = palette
        self.name = name

        self.rectangle = vectorio.Rectangle(
            pixel_shader=palette,
            color_index=GRAY,
            width=1,
            height=BAR_HEIGHT,
            x=TEXT_COLUMN_WIDTH,
            y=y_offset + BAR_PADDING + ROW_PADDING,
        )
        display_group.append(self.rectangle)

        self.limit_line = self._vertical_line(
            x=self.full_width - OVER_LIMIT_WIDTH,
            y=y_offset,
        )
        display_group.append(self.limit_line)

        display_group.append(self._metric_label(name, y=y_offset))

        if left_label:
            display_group.append(self._metric_label(left_label, x=TEXT_COLUMN_WIDTH + ROW_PADDING, y=y_offset))

        if right_label:
            display_group.append(
                self._metric_label(right_label, x=self.full_width - ROW_PADDING, y=y_offset, anchor_point=(1, 0.5))
            )

    def update(self, value, limit):
        percentage = value / limit * 100
        self.rectangle.width = self._bar_length_by_percentage(percentage)

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
            anchored_position=(x, y + ROW_HEIGHT // 2),
            anchor_point=anchor_point,
        )

    def _bar_length_by_percentage(self, percentage):
        """Return the length of the bar in pixels given a percentage."""
        theoretical = int((self.full_width - TEXT_COLUMN_WIDTH - OVER_LIMIT_WIDTH) * percentage / 100)

        return max(1, theoretical)


class VsAverageGauge(ExceedableLimitGauge):
    def __init__(self, name, full_width, display_group, palette, y_offset, left_label=None, right_label=None):
        super().__init__(name, full_width, display_group, palette, y_offset)


    def update_from_history(self, history: list[int]):
        current_value = history[0]
        average = sum(history) // len(history)
        sample_variance = sum((x - average) ** 2 for x in history) // len(history)
        std_dev = math.sqrt(sample_variance)

        print(f"{self.name}: {current_value=} {average=} {std_dev=}")

        self.update(current_value, average)
        self.rectangle.color_index = self._color_by_variance(current_value, std_dev, average)

    def _color_by_variance(self, value, std_dev, average):
        """Return the color of the bar given a percentage."""
        if value < average - std_dev:
            return GREEN
        if value < average + std_dev:
            return YELLOW
        return RED
