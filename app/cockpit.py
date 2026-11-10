"""Projekt-Cockpit – Desktop-Programm.

Zeigt die Cockpit-Oberfläche (web/index.html) in einem eigenen Fenster und
übernimmt, was ein Browser nicht darf:
  * Links zu Dateien, Ordnern, Mails und Webseiten im passenden Programm öffnen
  * Dateien per Drag & Drop aus dem Explorer verknüpfen
  * die Excel-Datenbasis direkt lesen und schreiben (inkl. täglicher Sicherung)
"""
import base64
import datetime as dt
import functools
import json
import logging
import logging.handlers
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.parse
import traceback
import webbrowser

import webview

try:
    from version import VERSION
except Exception:
    VERSION = "dev"

APP_NAME = "Projekt-Cockpit"
HTTP_PORT = 47318  # fester Port, damit der Browser-Zwischenspeicher zwischen Starts erhalten bleibt
IS_WIN = sys.platform.startswith("win")
URL_PREFIXES = ("http:", "https:", "mailto:", "ftp:", "onenote:", "ms-", "teams:")


def app_dir():
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    d = os.path.join(base, "ProjektCockpit")
    os.makedirs(d, exist_ok=True)
    return d


def resource(rel):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, rel)


CONFIG_FILE = os.path.join(app_dir(), "config.json")
LOG_FILE = os.path.join(app_dir(), "cockpit.log")

log = logging.getLogger("cockpit")
try:
    _h = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=512_000, backupCount=2, encoding="utf-8")
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(_h)
    log.setLevel(logging.INFO)
except Exception:
    pass


def _excepthook(t, v, tb):
    log.error("Unbehandelter Fehler:\n%s", "".join(traceback.format_exception(t, v, tb)))


sys.excepthook = _excepthook
_cfg_lock = threading.Lock()


def read_config():
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def write_config(cfg):
    with _cfg_lock:
        tmp = CONFIG_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=1)
        os.replace(tmp, CONFIG_FILE)


def is_url(p):
    return p.lower().startswith(URL_PREFIXES)


def clean_path(p):
    p = str(p or "").strip().strip('"').strip("'").strip()
    if p.lower().startswith("file:"):
        from urllib.request import url2pathname
        u = urllib.parse.urlparse(p)
        path = url2pathname(u.path)
        p = ("\\\\" + u.netloc + path) if u.netloc else path
    return os.path.expandvars(os.path.expanduser(p))


def start_file(target):
    if IS_WIN:
        os.startfile(target)  # öffnet mit dem verknüpften Programm (Word, Excel, Outlook …)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", target])
    else:
        subprocess.Popen(["xdg-open", target])


def mtime_ms(path):
    return int(os.path.getmtime(path) * 1000)


def safe_api(cls):
    """Jeder Fehler im Programmkern wird protokolliert und als {'__error': …} an die Oberfläche gemeldet,
    statt still zu verschwinden."""
    for name, fn in list(vars(cls).items()):
        if name.startswith("_") or not callable(fn):
            continue

        def make(f, n):
            @functools.wraps(f)
            def wrapper(self, *a, **kw):
                try:
                    return f(self, *a, **kw)
                except Exception as e:
                    log.error("Fehler in %s: %s\n%s", n, e, traceback.format_exc())
                    return {"__error": f"{type(e).__name__}: {e}"}

            return wrapper

        setattr(cls, name, make(fn, name))
    return cls


# ---------- Dateidialoge: zuerst nativ über Windows, sonst über pywebview ----------
def _wd():
    if not IS_WIN:
        return None
    try:
        import windialogs

        return windialogs
    except Exception as e:
        log.warning("Native Dialoge nicht verfügbar: %s", e)
        return None


def _as_list(r):
    if not r:
        return []
    return [r] if isinstance(r, str) else list(r)


@safe_api
class Api:
    """Alle Methoden sind in JavaScript als window.pywebview.api.<name>(...) erreichbar."""

    def __init__(self):
        self._window = None

    # ---------- Einstellungen ----------
    def get_config(self):
        return read_config()

    def set_config(self, key, value):
        cfg = read_config()
        cfg[key] = value
        write_config(cfg)
        return True

    # ---------- Links ----------
    def open_path(self, path):
        p = clean_path(path)
        if not p:
            return {"ok": False, "error": "Kein Pfad angegeben."}
        try:
            if is_url(p):
                if p.lower().startswith(("http:", "https:")):
                    webbrowser.open(p)
                else:
                    start_file(p)
                return {"ok": True}
            if not os.path.exists(p):
                return {"ok": False, "error": f"Nicht gefunden: {p}"}
            start_file(p)
            return {"ok": True}
        except Exception as e:  # z. B. keine Anwendung für den Dateityp
            return {"ok": False, "error": f"Konnte nicht geöffnet werden: {e}"}

    def reveal(self, path):
        p = clean_path(path)
        if not os.path.exists(p):
            parent = os.path.dirname(p)
            if parent and os.path.isdir(parent):
                start_file(parent)
                return {"ok": True}
            return {"ok": False, "error": f"Nicht gefunden: {p}"}
        try:
            if IS_WIN:
                if os.path.isdir(p):
                    os.startfile(p)
                else:
                    subprocess.Popen(["explorer", "/select,", os.path.normpath(p)])
            else:
                start_file(p if os.path.isdir(p) else os.path.dirname(p))
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def exists(self, paths):
        out = []
        for p in paths or []:
            q = clean_path(p)
            out.append(True if is_url(q) else os.path.exists(q))
        return out

    def _open_dialog(self, multiple, file_types=None, title=None):
        wd = _wd()
        if wd:
            try:
                return wd.open_files(multiple=multiple, file_types=file_types, title=title)
            except Exception as e:
                log.warning("Nativer Öffnen-Dialog fehlgeschlagen, nutze pywebview: %s", e)
        kw = {"allow_multiple": multiple}
        if file_types:
            kw["file_types"] = file_types
        return _as_list(self._window.create_file_dialog(webview.OPEN_DIALOG, **kw))

    def _save_dialog(self, name, file_types):
        wd = _wd()
        if wd:
            try:
                return wd.save_file(default_name=name, file_types=file_types)
            except Exception as e:
                log.warning("Nativer Speichern-Dialog fehlgeschlagen, nutze pywebview: %s", e)
        r = _as_list(self._window.create_file_dialog(webview.SAVE_DIALOG, save_filename=name, file_types=file_types))
        return r[0] if r else None

    def _folder_dialog(self):
        wd = _wd()
        if wd:
            try:
                return wd.pick_folder()
            except Exception as e:
                log.warning("Nativer Ordner-Dialog fehlgeschlagen, nutze pywebview: %s", e)
        r = _as_list(self._window.create_file_dialog(webview.FOLDER_DIALOG))
        return r[0] if r else None

    def pick_files(self):
        r = self._open_dialog(True, title="Dateien verknüpfen")
        log.info("Dateien gewählt: %s", r)
        return r

    def pick_folder(self):
        r = self._folder_dialog()
        log.info("Ordner gewählt: %s", r)
        return r

    def clipboard_files(self):
        wd = _wd()
        if not wd:
            return []
        r = wd.clipboard_files()
        log.info("Zwischenablage: %d Datei(en)", len(r))
        return r

    def log_js(self, msg):
        log.info("Oberfläche: %s", str(msg)[:500])
        return True

    def get_info(self):
        return {"version": VERSION, "log": LOG_FILE, "dir": app_dir(), "python": sys.version.split()[0],
                "pywebview": getattr(webview, "__version__", "?")}

    # ---------- Excel-Datenbasis ----------
    def choose_data_file(self, new):
        types = ("Excel-Arbeitsmappe (*.xlsx)",)
        if new:
            p = self._save_dialog("Projekt-Cockpit.xlsx", types)
            if not p:
                return None
            return p if p.lower().endswith(".xlsx") else p + ".xlsx"
        r = self._open_dialog(False, types, title="Cockpit-Excel öffnen")
        return r[0] if r else None

    def mtime(self, path):
        try:
            return mtime_ms(clean_path(path))
        except Exception:
            return None

    def read_b64(self, path):
        p = clean_path(path)
        try:
            with open(p, "rb") as f:
                data = f.read()
            return {"ok": True, "b64": base64.b64encode(data).decode("ascii"), "mtime": mtime_ms(p)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _backup(self, p):
        """Einmal pro Tag eine Sicherungskopie vor dem ersten Überschreiben (letzte 30 Tage)."""
        if not os.path.exists(p):
            return
        bdir = os.path.join(app_dir(), "Sicherungen")
        os.makedirs(bdir, exist_ok=True)
        stem = os.path.splitext(os.path.basename(p))[0]
        target = os.path.join(bdir, f"{stem}_{dt.date.today():%Y-%m-%d}.xlsx")
        if not os.path.exists(target):
            shutil.copy2(p, target)
            olds = sorted(f for f in os.listdir(bdir) if f.startswith(stem + "_") and f.endswith(".xlsx"))
            for f in olds[:-30]:
                try:
                    os.remove(os.path.join(bdir, f))
                except OSError:
                    pass

    def write_b64(self, path, b64):
        p = clean_path(path)
        data = base64.b64decode(b64)
        try:
            self._backup(p)
        except Exception:
            pass
        tmp = os.path.join(os.path.dirname(p) or ".", f".~{os.path.basename(p)}.tmp")
        try:
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, p)  # atomar: bei Absturz bleibt die alte Datei vollständig erhalten
            return {"ok": True, "mtime": mtime_ms(p)}
        except PermissionError as e:
            try:
                os.remove(tmp)
            except OSError:
                pass
            return {"ok": False, "locked": True, "error": str(e)}
        except Exception as e:
            try:
                os.remove(tmp)
            except OSError:
                pass
            return {"ok": False, "error": str(e)}

    # ---------- Exporte ----------
    def save_as(self, name, b64):
        ext = os.path.splitext(name)[1].lower()
        types = {".xlsx": ("Excel-Arbeitsmappe (*.xlsx)",), ".html": ("HTML (*.html)",), ".csv": ("CSV (*.csv)",)}.get(ext, ("Alle Dateien (*.*)",))
        p = self._save_dialog(name, types)
        if not p:
            return {"ok": False}
        if ext and not p.lower().endswith(ext):
            p += ext
        try:
            with open(p, "wb") as f:
                f.write(base64.b64decode(b64))
            return {"ok": True, "path": p}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def open_html(self, html):
        """Bericht im Standardbrowser öffnen (dort drucken bzw. als PDF speichern)."""
        fd, p = tempfile.mkstemp(prefix="Cockpit-Bericht_", suffix=".html")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(html)
        start_file(p)
        return True


def bind_drop(window):
    """Leitet Dateien, die aus dem Explorer ins Fenster gezogen werden, mit vollem Pfad an die Oberfläche."""
    try:
        from webview.dom import DOMEventHandler
    except Exception as e:
        log.warning("Drag & Drop nicht verfügbar (webview.dom): %s", e)
        return

    def on_drop(e):
        try:
            files = (e.get("dataTransfer") or {}).get("files") or []
            paths = [f.get("pywebviewFullPath") for f in files if f.get("pywebviewFullPath")]
            log.info("Drop: %d Datei(en), %d mit Pfad", len(files), len(paths))
            if paths:
                window.evaluate_js(
                    f"window.__dropFiles && window.__dropFiles({json.dumps(paths)}, {int(e.get('clientX', 0))}, {int(e.get('clientY', 0))})"
                )
        except Exception as ex:
            log.error("Drop-Verarbeitung fehlgeschlagen: %s\n%s", ex, traceback.format_exc())

    try:
        window.dom.document.events.dragover += DOMEventHandler(lambda e: None, True, True, debounce=200)
        window.dom.document.events.drop += DOMEventHandler(on_drop, True, True)
        log.info("Drag & Drop angebunden")
    except Exception as e:
        log.error("Drag & Drop konnte nicht angebunden werden: %s\n%s", e, traceback.format_exc())


def clear_http_cache(storage):
    """Zwischengespeicherte Seiten löschen, damit nach einem Update immer die neue Oberfläche geladen wird.
    Gespeicherte Daten (Local Storage, Einstellungen) bleiben erhalten."""
    for sub in ("Cache", "Code Cache", "GPUCache", "Service Worker"):
        for root in (os.path.join(storage, "EBWebView", "Default"), os.path.join(storage, "Default"), storage):
            d = os.path.join(root, sub)
            if os.path.isdir(d):
                try:
                    shutil.rmtree(d, ignore_errors=True)
                    log.info("Cache geleert: %s", d)
                except Exception:
                    pass


def main():
    api = Api()
    cfg = read_config()
    log.info("Start %s %s, Python %s, pywebview %s", APP_NAME, VERSION, sys.version.split()[0], getattr(webview, "__version__", "?"))
    window = webview.create_window(
        f"{APP_NAME} {VERSION}",
        url=resource(os.path.join("web", "index.html")),
        js_api=api,
        width=cfg.get("w", 1440),
        height=cfg.get("h", 900),
        min_size=(900, 600),
        text_select=True,
        confirm_close=False,
    )
    api._window = window

    def on_loaded():
        log.info("Seite geladen – Programmkern-Funktionen: %s", ", ".join(n for n in dir(api) if not n.startswith("_") and callable(getattr(api, n))))
        bind_drop(window)

    window.events.loaded += on_loaded

    def on_closing():
        try:
            c = read_config()
            c["w"], c["h"] = int(window.width), int(window.height)
            write_config(c)
        except Exception:
            pass

    try:
        window.events.closing += on_closing
    except Exception:
        pass

    storage = os.path.join(app_dir(), "webview")
    clear_http_cache(storage)
    kwargs = dict(private_mode=False, storage_path=storage, http_server=True, debug="--debug" in sys.argv)
    try:
        webview.start(http_port=HTTP_PORT, **kwargs)
    except (TypeError, OSError):  # ältere pywebview-Version ohne http_port oder Port belegt
        webview.start(**kwargs)


if __name__ == "__main__":
    main()
