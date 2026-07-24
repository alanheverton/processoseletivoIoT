from machine import Pin
from time import sleep_ms, ticks_diff, ticks_ms


LDR_PIN = 34
RESET_BUTTON_PIN = 27

MICRO_STOP_LIMIT_MS = 5000
LIGHT_DEBOUNCE_MS = 30
BUTTON_DEBOUNCE_MS = 40
POLL_INTERVAL_MS = 10

READY_MESSAGE = "Contador de Producao Inicializado"
PIECE_MESSAGE = "Peca detectada! Total: {}"
CYCLE_TIME_MESSAGE = "Tempo de ciclo: {} ms"
MICRO_STOP_MESSAGE = "Alerta: Micro-parada detectada!"
RESET_MESSAGE = "Turno resetado com sucesso. Contadores zerados."


class ProductionCounter:
    def __init__(self):
        self._light_sensor = Pin(LDR_PIN, Pin.IN)
        self._reset_button = Pin(RESET_BUTTON_PIN, Pin.IN, Pin.PULL_UP)

        now = ticks_ms()
        light_blocked = bool(self._light_sensor.value())
        button_pressed = self._reset_button.value() == 0

        self._piece_count = 0
        self._last_piece_ms = now
        self._piece_in_progress = False

        self._light_raw_blocked = light_blocked
        self._light_stable_blocked = light_blocked
        self._light_changed_ms = now
        self._blocked_since_ms = now if light_blocked else None
        self._micro_stop_reported = False

        self._button_raw_pressed = button_pressed
        self._button_stable_pressed = button_pressed
        self._button_changed_ms = now

        print(READY_MESSAGE)

    def _update_light(self, now):
        blocked = bool(self._light_sensor.value())
        if blocked != self._light_raw_blocked:
            self._light_raw_blocked = blocked
            self._light_changed_ms = now

        if (
            blocked != self._light_stable_blocked
            and ticks_diff(now, self._light_changed_ms) >= LIGHT_DEBOUNCE_MS
        ):
            self._light_stable_blocked = blocked
            if blocked:
                self._start_blockage(now)
            else:
                self._finish_blockage(now)

    def _start_blockage(self, now):
        self._blocked_since_ms = now
        self._micro_stop_reported = False
        self._piece_in_progress = True

    def _finish_blockage(self, now):
        self._blocked_since_ms = None
        self._micro_stop_reported = False
        if not self._piece_in_progress:
            return

        self._piece_in_progress = False
        self._piece_count += 1
        cycle_time_ms = ticks_diff(now, self._last_piece_ms)
        self._last_piece_ms = now
        print(PIECE_MESSAGE.format(self._piece_count))
        print(CYCLE_TIME_MESSAGE.format(cycle_time_ms))

    def _check_micro_stop(self, now):
        if (
            self._light_stable_blocked
            and not self._micro_stop_reported
            and ticks_diff(now, self._blocked_since_ms) >= MICRO_STOP_LIMIT_MS
        ):
            self._micro_stop_reported = True
            print(MICRO_STOP_MESSAGE)

    def _update_button(self, now):
        pressed = self._reset_button.value() == 0
        if pressed != self._button_raw_pressed:
            self._button_raw_pressed = pressed
            self._button_changed_ms = now

        if (
            pressed != self._button_stable_pressed
            and ticks_diff(now, self._button_changed_ms) >= BUTTON_DEBOUNCE_MS
        ):
            self._button_stable_pressed = pressed
            if pressed:
                self._reset_shift(now)

    def _reset_shift(self, now):
        self._piece_count = 0
        self._last_piece_ms = now
        self._piece_in_progress = False
        self._micro_stop_reported = False
        self._blocked_since_ms = now if self._light_stable_blocked else None
        print(RESET_MESSAGE)

    def _poll_once(self):
        now = ticks_ms()
        self._update_light(now)
        self._update_button(now)
        self._check_micro_stop(now)

    def run(self):
        while True:
            self._poll_once()
            sleep_ms(POLL_INTERVAL_MS)


if __name__ == "__main__":
    ProductionCounter().run()
