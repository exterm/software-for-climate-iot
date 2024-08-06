class CO2Alert:
    def __init__(self, notifier, co2_unsafe_over: int, co2_safe_under: int):
        self.co2_unsafe_over = co2_unsafe_over
        self.co2_safe_under = co2_safe_under
        self.notifier = notifier
        self.co2_max_while_over = 0
        self.active = False
        print(f"CO2 thresholds set to {self.co2_unsafe_over} ppm (unsafe) and {self.co2_safe_under} ppm (safe).")

    def alert_maybe(self, co2_ppm: int) -> None:
        if co2_ppm > self.co2_unsafe_over:
            self.co2_max_while_over = max(self.co2_max_while_over, co2_ppm)
            if not self.active:
                self.notifier.send_alert(f"Reached unsafe CO2 levels ({co2_ppm}).")
                self.active = True
        elif self.active and co2_ppm < self.co2_safe_under:
            self.notifier.send_alert(f"CO2 levels returned to normal. Max level was {self.co2_max_while_over}.")
            self.active = False
            self.co2_max_while_over = 0
