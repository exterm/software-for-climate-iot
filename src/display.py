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

GREEN_HEX = 0x008000
YELLOW_HEX = 0xEEEE00
RED_HEX = 0xFF0000
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
            "CO2e",
            full_width,
            display_group,
            palette,
            rows[0],
            "g/kWh",
        )

        # grid stress

        self.demand_gauge = VsAverageGauge(
            "Demand",
            full_width,
            display_group,
            palette,
            rows[1],
            "MW",
        )

        # price

        self.energy_usage_gauge = ExceedableLimitGauge(
            "Usage",
            full_width,
            display_group,
            palette,
            rows[2],
            "kWh",
        )

    def _price_label_text(self, price_centicents):
        """Return a string representation of the price in cents per kWh."""
        return f"{price_centicents/100:.2f} $/kWh"

    def update(
        self,
        carbon_intensity_history: list[int] = [],
        power_consumption_history: list[int] = [],
        energy_usage_kwh=0,
        tier_limit=0,
        tier1_price=0,
        tier2_price=0,
    ):
        """Update the dashboard with the latest data."""
        self.grid_intensity_gauge.update_from_history(carbon_intensity_history)

        self.demand_gauge.update_from_history(power_consumption_history)

        self.energy_usage_gauge.update(energy_usage_kwh, self.tier1_limit)


class Gauge:
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

        display_group.append(self._metric_label(name, y=y_offset))

        if left_label is not None:
            self.left_label = self._metric_label(left_label, x=TEXT_COLUMN_WIDTH + ROW_PADDING, y=y_offset)
            display_group.append(self.left_label)

        if right_label is not None:
            self.right_label = self._metric_label(right_label, x=self.full_width - ROW_PADDING, y=y_offset, anchor_point=(1, 0.5))
            display_group.append(self.right_label)

    def update(self, value, limit):
        percentage = value / limit * 100
        self.rectangle.width = self._bar_length_by_percentage(percentage)

    def _vertical_line(self, x, y, color=WHITE):
        """Return a vertical line at the given x coordinate."""
        return vectorio.Rectangle(
            pixel_shader=self.palette,
            color_index=color,
            width=2,
            height=ROW_HEIGHT - 2 * ROW_PADDING,
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

class ExceedableLimitGauge(Gauge):
    def __init__(self, name, full_width, display_group, palette, y_offset, unit):
        self.unit = unit

        super().__init__(name, full_width, display_group, palette, y_offset, "")

        self.limit_line = self._vertical_line(
            x=full_width - OVER_LIMIT_WIDTH,
            y=y_offset,
        )
        display_group.append(self.limit_line)

    def update(self, value, limit):
        super().update(value, limit)

        self.left_label.text = f"{value} {self.unit}"


class VsAverageGauge(Gauge):
    def __init__(self, name, full_width, display_group, palette, y_offset, unit):
        super().__init__(name, full_width, display_group, palette, y_offset, "")
        self.unit = unit

        self.rectangle.color_index = GREEN

        self.close_rectangle = vectorio.Rectangle(
            pixel_shader=palette,
            color_index=BLACK,
            width=1,
            height=BAR_HEIGHT,
            x=full_width + 1,
            y=y_offset + BAR_PADDING + ROW_PADDING,
        )
        display_group.append(self.close_rectangle)

        self.over_rectangle = vectorio.Rectangle(
            pixel_shader=palette,
            color_index=BLACK,
            width=1,
            height=BAR_HEIGHT,
            x=full_width + 1,
            y=y_offset + BAR_PADDING + ROW_PADDING,
        )
        display_group.append(self.over_rectangle)

    def update_from_history(self, history: list[int]):
        current_value = history[0]
        median = self._calculate_percentile(history, 0.5)
        good_up_to = self._calculate_percentile(history, 0.4)
        bad_from = self._calculate_percentile(history, 0.6)

        print(f"{self.name}: {current_value=} {median=} {good_up_to=} {bad_from=}")

        self.left_label.text = f"{current_value} {self.unit}"

        # "good" bar
        good_width = self._bar_length_by_relative_value(current_value, median, 0, good_up_to)
        self.rectangle.width = max(1, good_width)

        # "close" bar
        close_width = self._bar_length_by_relative_value(current_value, median, good_up_to, bad_from)

        if close_width == 0:
            self.close_rectangle.color_index = BLACK
            self.close_rectangle.x = self.full_width + 1
        else:
            self.close_rectangle.color_index = YELLOW
            self.close_rectangle.width = close_width
            self.close_rectangle.x = good_width + TEXT_COLUMN_WIDTH

        # "over" bar
        over_width = self._bar_length_by_relative_value(current_value, median, bad_from)

        if over_width == 0:
            self.over_rectangle.color_index = BLACK
            self.over_rectangle.x = self.full_width + 1
        else:
            self.over_rectangle.color_index = RED
            self.over_rectangle.width = over_width
            self.over_rectangle.x = good_width + close_width + TEXT_COLUMN_WIDTH

    def _bar_length_by_relative_value(self, value, comparison, lower_bound, upper_bound=None):
        """Return the width of the bar given a value and a comparison value."""
        if value <= lower_bound:
            return 0

        if upper_bound and value >= upper_bound:
            value = upper_bound

        return self._bar_length_by_percentage((value - lower_bound) / comparison * 100)

    def _calculate_percentile(self, data, percentile):
        data = sorted(data)
        theoretical_index = (len(data) - 1) * percentile
        lower_index = int(theoretical_index)
        upper_index = lower_index + 1

        if upper_index >= len(data):
            return data[lower_index]
        lower_value = data[lower_index]
        upper_value = data[upper_index]

        return lower_value + (upper_value - lower_value) * (theoretical_index - lower_index)
