"""Setzt die Versionsnummer aus der Datei VERSION in den Programmkern und die Oberfläche (nur im Build)."""
import os
import re

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ver = open(os.path.join(root, "VERSION"), encoding="utf-8").read().strip()
assert re.fullmatch(r"\d+\.\d+\.\d+", ver), f"Ungültige Version: {ver!r}"
with open(os.path.join(root, "app", "version.py"), "w", encoding="utf-8") as f:
    f.write(f'VERSION = "{ver}"\n')
p = os.path.join(root, "web", "index.html")
html = open(p, encoding="utf-8").read()
tag = "const APP_VERSION='dev';"
assert html.count(tag) == 1, "Versions-Platzhalter in index.html nicht gefunden"
open(p, "w", encoding="utf-8").write(html.replace(tag, f"const APP_VERSION='{ver}';"))
print("Version", ver)
if os.environ.get("GITHUB_OUTPUT"):
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
        f.write(f"version={ver}\n")
