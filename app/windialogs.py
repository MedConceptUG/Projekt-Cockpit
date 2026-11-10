"""Native Windows-Dateidialoge über die Windows-API (comdlg32/shell32).

Unabhängig von der Fensterbibliothek und aus jedem Thread aufrufbar – der Aufrufer-Thread
wird dafür als COM-STA initialisiert. Rückgabe: Pfad(e) oder None/[] bei Abbruch.
"""
import ctypes
import os
from ctypes import wintypes

comdlg32 = ctypes.WinDLL("comdlg32")
shell32 = ctypes.WinDLL("shell32")
ole32 = ctypes.WinDLL("ole32")
user32 = ctypes.WinDLL("user32")

OFN_OVERWRITEPROMPT = 0x00000002
OFN_HIDEREADONLY = 0x00000004
OFN_NOCHANGEDIR = 0x00000008
OFN_PATHMUSTEXIST = 0x00000800
OFN_FILEMUSTEXIST = 0x00001000
OFN_ALLOWMULTISELECT = 0x00000200
OFN_EXPLORER = 0x00080000
OFN_LONGNAMES = 0x00200000

BIF_RETURNONLYFSDIRS = 0x00000001
BIF_NEWDIALOGSTYLE = 0x00000040
BIF_EDITBOX = 0x00000010

BUF_CHARS = 65536


class OPENFILENAMEW(ctypes.Structure):
    _fields_ = [
        ("lStructSize", wintypes.DWORD),
        ("hwndOwner", wintypes.HWND),
        ("hInstance", wintypes.HINSTANCE),
        ("lpstrFilter", wintypes.LPCWSTR),
        ("lpstrCustomFilter", wintypes.LPWSTR),
        ("nMaxCustFilter", wintypes.DWORD),
        ("nFilterIndex", wintypes.DWORD),
        ("lpstrFile", wintypes.LPWSTR),
        ("nMaxFile", wintypes.DWORD),
        ("lpstrFileTitle", wintypes.LPWSTR),
        ("nMaxFileTitle", wintypes.DWORD),
        ("lpstrInitialDir", wintypes.LPCWSTR),
        ("lpstrTitle", wintypes.LPCWSTR),
        ("Flags", wintypes.DWORD),
        ("nFileOffset", wintypes.WORD),
        ("nFileExtension", wintypes.WORD),
        ("lpstrDefExt", wintypes.LPCWSTR),
        ("lCustData", wintypes.LPARAM),
        ("lpfnHook", ctypes.c_void_p),
        ("lpTemplateName", wintypes.LPCWSTR),
        ("pvReserved", ctypes.c_void_p),
        ("dwReserved", wintypes.DWORD),
        ("FlagsEx", wintypes.DWORD),
    ]


class BROWSEINFOW(ctypes.Structure):
    _fields_ = [
        ("hwndOwner", wintypes.HWND),
        ("pidlRoot", ctypes.c_void_p),
        ("pszDisplayName", wintypes.LPWSTR),
        ("lpszTitle", wintypes.LPCWSTR),
        ("ulFlags", wintypes.UINT),
        ("lpfn", ctypes.c_void_p),
        ("lParam", wintypes.LPARAM),
        ("iImage", ctypes.c_int),
    ]


comdlg32.GetOpenFileNameW.argtypes = [ctypes.POINTER(OPENFILENAMEW)]
comdlg32.GetOpenFileNameW.restype = wintypes.BOOL
comdlg32.GetSaveFileNameW.argtypes = [ctypes.POINTER(OPENFILENAMEW)]
comdlg32.GetSaveFileNameW.restype = wintypes.BOOL
comdlg32.CommDlgExtendedError.restype = wintypes.DWORD
shell32.SHBrowseForFolderW.argtypes = [ctypes.POINTER(BROWSEINFOW)]
shell32.SHBrowseForFolderW.restype = ctypes.c_void_p
shell32.SHGetPathFromIDListW.argtypes = [ctypes.c_void_p, wintypes.LPWSTR]
shell32.SHGetPathFromIDListW.restype = wintypes.BOOL
ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, wintypes.DWORD]
ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
user32.GetForegroundWindow.restype = wintypes.HWND


def _sta():
    # 0x2 = COINIT_APARTMENTTHREADED; S_FALSE/RPC_E_CHANGED_MODE sind unkritisch
    try:
        ole32.CoInitializeEx(None, 0x2)
    except Exception:
        pass


def _filter(file_types):
    """('Excel-Arbeitsmappe (*.xlsx)', …) → 'Excel-Arbeitsmappe (*.xlsx)\\0*.xlsx\\0…\\0\\0'"""
    parts = []
    for ft in file_types or ("Alle Dateien (*.*)",):
        pat = ft[ft.rfind("(") + 1 : ft.rfind(")")] if "(" in ft else "*.*"
        parts += [ft, pat.replace(" ", ";")]
    return "\0".join(parts) + "\0\0"


def _ofn(buf, file_types, flags, title=None, def_ext=None, initial_dir=None, owner=None):
    ofn = OPENFILENAMEW()
    ofn.lStructSize = ctypes.sizeof(OPENFILENAMEW)
    ofn.hwndOwner = owner or user32.GetForegroundWindow()
    ofn.lpstrFilter = _filter(file_types)
    ofn.nFilterIndex = 1
    ofn.lpstrFile = ctypes.cast(buf, wintypes.LPWSTR)
    ofn.nMaxFile = BUF_CHARS
    ofn.lpstrTitle = title
    ofn.lpstrDefExt = def_ext
    ofn.lpstrInitialDir = initial_dir
    ofn.Flags = flags
    return ofn


def _check(ok):
    if not ok:
        err = comdlg32.CommDlgExtendedError()
        if err:
            raise OSError(f"Windows-Dateidialog meldet Fehler 0x{err:04X}")


def open_files(multiple=True, file_types=None, title=None, initial_dir=None, owner=None):
    _sta()
    buf = ctypes.create_unicode_buffer(BUF_CHARS)
    flags = OFN_EXPLORER | OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST | OFN_NOCHANGEDIR | OFN_HIDEREADONLY | OFN_LONGNAMES
    if multiple:
        flags |= OFN_ALLOWMULTISELECT
    ofn = _ofn(buf, file_types, flags, title=title, initial_dir=initial_dir, owner=owner)
    ok = comdlg32.GetOpenFileNameW(ctypes.byref(ofn))
    _check(ok)
    if not ok:
        return []
    raw = ctypes.wstring_at(ctypes.addressof(buf), BUF_CHARS).split("\0")
    items = []
    for x in raw:
        if not x:
            break
        items.append(x)
    if len(items) <= 1:
        return items
    folder = items[0]
    return [os.path.join(folder, name) for name in items[1:]]


def save_file(default_name="", file_types=None, title=None, initial_dir=None, owner=None):
    _sta()
    buf = ctypes.create_unicode_buffer(default_name or "", BUF_CHARS)
    flags = OFN_EXPLORER | OFN_OVERWRITEPROMPT | OFN_PATHMUSTEXIST | OFN_NOCHANGEDIR | OFN_HIDEREADONLY | OFN_LONGNAMES
    ext = os.path.splitext(default_name or "")[1].lstrip(".") or None
    ofn = _ofn(buf, file_types, flags, title=title, def_ext=ext, initial_dir=initial_dir, owner=owner)
    ok = comdlg32.GetSaveFileNameW(ctypes.byref(ofn))
    _check(ok)
    return buf.value if ok and buf.value else None


def pick_folder(title="Ordner wählen", owner=None):
    _sta()
    name = ctypes.create_unicode_buffer(260)
    bi = BROWSEINFOW()
    bi.hwndOwner = owner or user32.GetForegroundWindow()
    bi.pszDisplayName = ctypes.cast(name, wintypes.LPWSTR)
    bi.lpszTitle = title
    bi.ulFlags = BIF_RETURNONLYFSDIRS | BIF_NEWDIALOGSTYLE | BIF_EDITBOX
    pidl = shell32.SHBrowseForFolderW(ctypes.byref(bi))
    if not pidl:
        return None
    try:
        path = ctypes.create_unicode_buffer(32768)
        if shell32.SHGetPathFromIDListW(pidl, path):
            return path.value or None
        return None
    finally:
        ole32.CoTaskMemFree(pidl)


# ---------- Dateien aus der Zwischenablage (im Explorer Strg+C) ----------
CF_HDROP = 15
user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL
user32.CloseClipboard.restype = wintypes.BOOL
user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
user32.IsClipboardFormatAvailable.restype = wintypes.BOOL
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.GetClipboardData.restype = wintypes.HANDLE
shell32.DragQueryFileW.argtypes = [wintypes.HANDLE, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
shell32.DragQueryFileW.restype = wintypes.UINT


def clipboard_files():
    """Liefert die Pfade der Dateien/Ordner, die im Explorer mit Strg+C kopiert wurden."""
    import time

    if not user32.IsClipboardFormatAvailable(CF_HDROP):
        return []
    for _ in range(20):
        if user32.OpenClipboard(None):
            break
        time.sleep(0.05)
    else:
        raise OSError("Die Zwischenablage ist gerade von einem anderen Programm belegt.")
    try:
        h = user32.GetClipboardData(CF_HDROP)
        if not h:
            return []
        n = shell32.DragQueryFileW(h, 0xFFFFFFFF, None, 0)
        out = []
        for i in range(n):
            ln = shell32.DragQueryFileW(h, i, None, 0)
            buf = ctypes.create_unicode_buffer(ln + 1)
            shell32.DragQueryFileW(h, i, buf, ln + 1)
            out.append(buf.value)
        return out
    finally:
        user32.CloseClipboard()
