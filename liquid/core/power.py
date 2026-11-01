# SPDX-License-Identifier: GPL-3.0-only
"""UPower'ın toplam pil tahmini; menü açılırken D-Bus/komut beklemesi yok."""
from gi.repository import Gio

from .i18n import t


def duration(seconds):
    minutes = max(1, (int(seconds) + 59) // 60)
    hours, minutes = divmod(minutes, 60)
    parts = []
    if hours:
        parts.append(t("battery_hours").format(hours))
    if minutes:
        parts.append(t("battery_minutes").format(minutes))
    return " ".join(parts)


def estimate_text(state, empty=0, full=0):
    # org.freedesktop.UPower.Device.State: 1 charging, 2 discharging,
    # 3 empty, 4 fully charged, 5 pending charge, 6 pending discharge.
    if state == 4:
        return t("battery_full")
    if state == 3:
        return t("battery_empty")
    if state == 5:
        return t("battery_pending_charge")
    if state == 1:
        return (t("battery_time_to_full").format(duration(full)) if full > 0
                else t("battery_charging"))
    if state in (2, 6) and empty > 0:
        return t("battery_time_left").format(duration(empty))
    return t("battery_time_unavailable")


class BatteryEstimate:
    def __init__(self):
        self.proxy = None
        Gio.DBusProxy.new_for_bus(
            Gio.BusType.SYSTEM, Gio.DBusProxyFlags.DO_NOT_AUTO_START, None,
            "org.freedesktop.UPower", "/org/freedesktop/UPower/devices/DisplayDevice",
            "org.freedesktop.UPower.Device", None, self._ready)

    def _ready(self, source, result):
        try:
            self.proxy = Gio.DBusProxy.new_for_bus_finish(result)
        except Exception:
            self.proxy = None

    def text(self):
        def value(name, default=0):
            v = self.proxy.get_cached_property(name) if self.proxy else None
            return v.unpack() if v is not None else default
        if not value("IsPresent", False):
            return t("battery_time_unavailable")
        return estimate_text(value("State"), value("TimeToEmpty"), value("TimeToFull"))
