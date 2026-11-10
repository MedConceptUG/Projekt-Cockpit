"""Erzeugt dist/projekt-cockpit.html: die Browser-Version als eine einzige Datei (Excel-Bibliothek eingebettet)."""
import os

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(root, "web", "index.html"), encoding="utf-8").read()
lib = open(os.path.join(root, "web", "xlsx.mini.min.js"), encoding="utf-8").read().replace("</script", "<\\/script")
tag = '<script src="xlsx.mini.min.js"></script>'
assert html.count(tag) == 1, "Script-Tag der Excel-Bibliothek nicht gefunden"
os.makedirs(os.path.join(root, "dist"), exist_ok=True)
out = os.path.join(root, "dist", "projekt-cockpit.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html.replace(tag, "<script>" + lib + "</script>"))
print("geschrieben:", out)
