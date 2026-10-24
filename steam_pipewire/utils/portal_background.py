"""Flatpak: login autostart via org.freedesktop.portal.Background (RequestBackground).

Works across KDE, GNOME, and other desktops that implement xdg-desktop-portal; the host shows
a system dialog instead of writing an autostart file inside the sandbox.
"""

from __future__ import annotations

import logging
import secrets
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)

from PyQt6.QtCore import QMetaType, QObject, QVariant, pyqtSlot
from PyQt6.QtDBus import (
    QDBusConnection,
    QDBusInterface,
    QDBusMessage,
)


def portal_parent_window(widget) -> str:
    """Window handle for the portal (optional). Empty string is valid everywhere."""
    try:
        wh = widget.windowHandle()
        if wh is None:
            return ""
        # X11: helps some portal implementations parent the dialog
        from PyQt6.QtWidgets import QApplication

        if QApplication.platformName() == "xcb":
            return f"x11:{hex(int(wh.winId()))}"
    except Exception:
        pass
    return ""


def _flatpak_commandline(start_minimized: bool) -> List[str]:
    """Desktop entry Exec name + args (flatpak run is implied by the portal)."""
    cl = ["steam-audio-isolator"]
    if start_minimized:
        cl.append("--minimized")
    return cl


def _string_list_variant(values: List[str]) -> QVariant:
    """Wrap a string list so D-Bus sees ``as``, not ``av``.

    Qt maps a plain Python list inside an ``a{sv}`` map to a variant list
    (``av``). The portal expects ``commandline`` to be ``as``, so pin the
    variant type explicitly.
    """
    variant = QVariant(list(values))
    try:
        variant.convert(QMetaType(QMetaType.Type.QStringList.value))
    except Exception:
        logger.debug("Could not type Qt variant as QStringList", exc_info=True)
    return variant


def _portal_request_background(parent_window: str, options: dict) -> str:
    """Call RequestBackground with a correctly typed a{sv} options map.

    Uses QtDBus directly (no PyGObject/pydbus, which are not available in the
    25.08 runtime).
    """
    bus = QDBusConnection.sessionBus()
    if not bus.isConnected():
        raise RuntimeError("session bus is not available")

    iface = QDBusInterface(
        "org.freedesktop.portal.Desktop",
        "/org/freedesktop/portal/desktop",
        "org.freedesktop.portal.Background",
        bus,
    )
    if not iface.isValid():
        raise RuntimeError("org.freedesktop.portal.Background is not available")

    typed_options = {
        "handle_token": options["handle_token"],
        "reason": options["reason"],
        "autostart": options["autostart"],
        "commandline": _string_list_variant(options["commandline"]),
    }

    reply = iface.call("RequestBackground", parent_window, typed_options)
    if reply.type() == QDBusMessage.MessageType.Error:
        raise RuntimeError(reply.errorMessage() or "RequestBackground failed")
    args = reply.arguments()
    return str(args[0]) if args else ""


class PortalBackgroundRequest(QObject):
    """Async RequestBackground + listen for org.freedesktop.portal.Request::Response."""

    def __init__(
        self,
        parent: Optional[QObject],
        parent_window: str,
        autostart: bool,
        start_minimized: bool,
        on_done: Callable[[bool, str], None],
    ):
        super().__init__(parent)
        self._on_done = on_done
        self._requested_autostart = autostart
        self._handle_path: Optional[str] = None
        self._bus = QDBusConnection.sessionBus()
        self._connected = False

        token = "sai" + secrets.token_hex(6)
        reason = (
            "Start Steam Audio Isolator at login so PipeWire routing is ready when you play."
            if autostart
            else "Do not start Steam Audio Isolator automatically at login."
        )
        opts = {
            "handle_token": token,
            "reason": reason,
            "autostart": autostart,
            "commandline": _flatpak_commandline(start_minimized),
        }
        try:
            self._handle_path = _portal_request_background(parent_window, opts)
        except Exception as exc:
            self._finish(False, f"Portal error: {exc}")
            return

        if not self._handle_path:
            self._finish(False, "Portal returned an empty reply.")
            return

        ok = self._bus.connect(
            "org.freedesktop.portal.Desktop",
            self._handle_path,
            "org.freedesktop.portal.Request",
            "Response",
            self._on_response,
        )
        if not ok:
            self._finish(False, "Could not listen for portal response.")
            return
        self._connected = True

    def _finish(self, ok: bool, message: str) -> None:
        self._disconnect_response()
        self._close_request()
        try:
            self._on_done(ok, message)
        except Exception:
            logger.exception("portal on_done failed")
        self.deleteLater()

    def _disconnect_response(self) -> None:
        if self._connected and self._handle_path:
            try:
                self._bus.disconnect(
                    "org.freedesktop.portal.Desktop",
                    self._handle_path,
                    "org.freedesktop.portal.Request",
                    "Response",
                    self._on_response,
                )
            except Exception:
                pass
            self._connected = False

    def _close_request(self) -> None:
        if not self._handle_path:
            return
        try:
            iface = QDBusInterface(
                "org.freedesktop.portal.Desktop",
                self._handle_path,
                "org.freedesktop.portal.Request",
                self._bus,
            )
            iface.call("Close")
        except Exception:
            pass

    @pyqtSlot("uint", "QVariantMap")
    def _on_response(self, response: int, results: dict) -> None:
        if int(response) != 0:
            self._finish(False, "Autostart was not changed (dialog cancelled or denied).")
            return
        try:
            auto = bool(results.get("autostart", False))
        except Exception:
            auto = False
        if self._requested_autostart:
            if auto:
                self._finish(
                    True,
                    "Login autostart was updated. You can change it later in your desktop "
                    "session settings if needed.",
                )
            else:
                self._finish(False, "Login autostart was not enabled (check the system dialog or settings).")
        else:
            self._finish(True, "Login autostart disabled (or left unchanged by the system).")


def request_flatpak_login_autostart(
    parent_widget,
    autostart: bool,
    start_minimized: bool,
    on_done: Callable[[bool, str], None],
) -> bool:
    """Start a portal RequestBackground flow. Parents the request to parent_widget."""
    try:
        PortalBackgroundRequest(
            parent_widget,
            portal_parent_window(parent_widget),
            autostart,
            start_minimized,
            on_done,
        )
        return True
    except Exception as e:
        logger.exception("request_flatpak_login_autostart: %s", e)
        on_done(False, str(e))
        return False
