"""Liquid çekirdeği: tasarım, duvar kâğıdı, süreç, uygulama ve metin yardımcıları."""
import os

CONFIG = os.path.expanduser("~/.config/liquid")


def config_path(name):
    os.makedirs(CONFIG, exist_ok=True)
    return os.path.join(CONFIG, name)


def screen_geometry():
    """Birincil monitör (x, y, w, h)."""
    from gi.repository import Gdk
    disp = Gdk.Display.get_default()
    g = (disp.get_primary_monitor() or disp.get_monitor(0)).get_geometry()
    return g.x, g.y, g.width, g.height


def set_strut(gdk_window, top=0, bottom=0, x0=0, x1=0):
    """_NET_WM_STRUT(_PARTIAL): büyütülmüş pencereler çubuk/dock'un altına girmesin."""
    import subprocess
    try:
        xid = str(gdk_window.get_xid())
    except Exception:
        return
    vals = f"0, 0, {top}, {bottom}, 0, 0, 0, 0, {x0 if top else 0}, {x1 if top else 0}, " \
           f"{x0 if bottom else 0}, {x1 if bottom else 0}"
    for prop, v in (("_NET_WM_STRUT_PARTIAL", vals), ("_NET_WM_STRUT", f"0, 0, {top}, {bottom}")):
        subprocess.run(["xprop", "-id", xid, "-f", prop, "32c", "-set", prop, v],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
