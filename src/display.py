from framebufferio import FramebufferDisplay
import vectorio
import displayio
from adafruit_display_text.bitmap_label import Label
import terminalio


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

BAR_PADDING: int = 3
BAR_HEIGHT: int = 17
ROW_PADDING: int = 3
ROW_HEIGHT: int = BAR_HEIGHT + 2 * BAR_PADDING + 2 * ROW_PADDING
TEXT_COLUMN_WIDTH: int = 45
OVER_LIMIT_WIDTH: int = 75

HOURS_PER_DAY = 24


class Dashboard:
    """
    Display a personalized power supply dashboard from precomputed values.

    We'll display three horizontal gauges, one for each of the following:
    - current grid carbon intensity
    - current grid stress factor (calculated as a function of capacity and demand)
    - current energy price per kWh based on tiered pricing and cumulative usage
    """

    def __init__(self, display: FramebufferDisplay, tier1_limit, co2_safe_under, co2_unsafe_over):
        self.tier1_limit: int = tier1_limit

        palette = displayio.Palette(6)
        palette[BLACK] = BLACK_HEX
        palette[GREEN] = GREEN_HEX
        palette[YELLOW] = YELLOW_HEX
        palette[RED] = RED_HEX
        palette[WHITE] = WHITE_HEX
        palette[GRAY] = GRAY_HEX

        rows = [n * ROW_HEIGHT for n in range(4)]

        full_width = display.width
        display_group = displayio.Group()
        display.root_group = display_group

        self.grid_intensity_gauge = VsAverageGauge(
            "CO2e",
            full_width,
            display_group,
            palette,
            rows[0],
            "g/kWh",
        )

        self.demand_gauge = VsAverageGauge(
            "Demand",
            full_width,
            display_group,
            palette,
            rows[1],
            "MW",
        )

        self.energy_usage_gauge = ExceedableLimitGauge(
            "Usage",
            full_width,
            display_group,
            palette,
            rows[2],
            "kWh",
        )

        self.co2_gauge = ThresholdGauge(
            "CO2",
            full_width,
            display_group,
            palette,
            rows[3],
            "ppm",
            co2_safe_under,
            co2_unsafe_over,
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
        co2_ppm=0,
    ):
        """Update the dashboard with the latest data."""
        self.grid_intensity_gauge.update_from_history(carbon_intensity_history)

        self.demand_gauge.update_from_history(power_consumption_history)

        self.energy_usage_gauge.update(energy_usage_kwh, self.tier1_limit)

        self.co2_gauge.update(co2_ppm)


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

    def _init_tricolor_segments(self, display_group, y_offset):
        """Turn this gauge's primary bar green and add yellow/red follow-on segments."""
        self.rectangle.color_index = GREEN
        self.yellow_rectangle = self._segment_rectangle(y_offset)
        self.red_rectangle = self._segment_rectangle(y_offset)
        display_group.append(self.yellow_rectangle)
        display_group.append(self.red_rectangle)

    def _segment_rectangle(self, y_offset):
        return vectorio.Rectangle(
            pixel_shader=self.palette,
            color_index=BLACK,
            width=1,
            height=BAR_HEIGHT,
            x=self.full_width + 1,
            y=y_offset + BAR_PADDING + ROW_PADDING,
        )

    def _render_tricolor(self, green_width, yellow_width, red_width):
        self.rectangle.width = max(1, green_width)
        self._place_segment(self.yellow_rectangle, YELLOW, yellow_width, TEXT_COLUMN_WIDTH + green_width)
        self._place_segment(self.red_rectangle, RED, red_width, TEXT_COLUMN_WIDTH + green_width + yellow_width)

    def _place_segment(self, rect, color, width, x):
        if width <= 0:
            rect.color_index = BLACK
            rect.x = self.full_width + 1
        else:
            rect.color_index = color
            rect.width = width
            rect.x = x

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

        self._init_tricolor_segments(display_group, y_offset)

    def update_from_history(self, history: list[int]):
        current_value = history[-1]

        restricted_history = history[-HOURS_PER_DAY:]

        week_median = self._calculate_percentile(history, 0.5)
        day_median = self._calculate_percentile(restricted_history, 0.5)

        good_up_to = min(week_median, day_median)
        bad_from = max(week_median, day_median)

        center = (good_up_to + bad_from) / 2

        print(f"{self.name}: {current_value=} {week_median=} {day_median=}")

        self.left_label.text = f"{current_value} {self.unit}"

        good_width = self._bar_length_by_relative_value(current_value, center, 0, good_up_to)
        close_width = self._bar_length_by_relative_value(current_value, center, good_up_to, bad_from)
        over_width = self._bar_length_by_relative_value(current_value, center, bad_from)

        self._render_tricolor(good_width, close_width, over_width)

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


class ThresholdGauge(Gauge):
    def __init__(self, name, full_width, display_group, palette, y_offset, unit, safe_under, unsafe_over):
        self.unit = unit
        self.safe_under = safe_under
        self.unsafe_over = unsafe_over
        self.full_scale = unsafe_over * 2

        super().__init__(name, full_width, display_group, palette, y_offset, "")

        self._init_tricolor_segments(display_group, y_offset)

    def update(self, value):
        self.left_label.text = f"{value} {self.unit}" if value else ""

        capped = min(value, self.full_scale)
        green_end = min(capped, self.safe_under)
        yellow_end = min(capped, self.unsafe_over)

        green_width = self._bar_length_for(green_end)
        yellow_width = self._bar_length_for(yellow_end) - green_width
        red_width = self._bar_length_for(capped) - green_width - yellow_width

        self._render_tricolor(green_width, yellow_width, red_width)

    def _bar_length_for(self, value):
        return int((self.full_width - TEXT_COLUMN_WIDTH - ROW_PADDING) * value / self.full_scale)
