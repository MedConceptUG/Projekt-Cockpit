# Projekt-Cockpit

**Ein Plan für Projekte und Tagesgeschäft – mit Ursache und Wirkung.**
Kostenlos, quelloffen (MIT-Lizenz), ohne Installation, ohne Cloud: deine Daten liegen in deiner eigenen Excel-Datei.

Für Projektleiterinnen und Projektleiter jeder Branche, die mehrere Projekte und das Tagesgeschäft gleichzeitig steuern
und jederzeit sehen wollen: **Wer macht was bis wann – und warum?**

## Was es kann
- **Gantt mit Abteilungs-Swimlanes** – je Projekt eine Zeile pro Abteilung, Phasen, Meilensteine als senkrechte Linien, Balken per Maus ziehen, verlängern, verbinden.
- **Events im ToDo** – Telefonat, Mail, Problem, Entscheidung, Freigabe … einfach als Symbol in den Balken ziehen. Aus einem Event per Ziehen ein neues ToDo machen.
- **Ursache → Wirkung** – Pfeile zeigen, was woraus folgt; verschiebt sich etwas, rücken die Folgen nach (mit Vorschau).
- **Kritische Punkte im Blick** – Probleme ohne Maßnahme, bewusst übergangene Checklistenpunkte, überfällige Termine.
- **Checklisten & Vorlagen** je Aufgabe, **Urlaub/Betriebsurlaub**, der Balken automatisch verlängert.
- **Design Reviews**: Stand seit dem letzten Review per Klick als PDF oder Word fixieren – mit Gantt, offenen Punkten und Historie.
- **PDF-Export** des Gesamtplans und je Abteilung (passt auf A3/A4 quer).
- **Vollständige Historie** mit Wiederherstellen, **Strg+Z / Strg+Y**.
- **Echte Links** zu Word, Excel, PDF, Ordnern, Outlook-Mails und Webseiten (Desktop-Programm).

## Herunterladen
Rechts unter **Releases** die neueste Version öffnen:
- **Projekt-Cockpit.exe** – Desktop-Programm für Windows 10/11, ohne Installation. Einfach starten.
  Warnt Windows („Der Computer wurde durch Windows geschützt“): *Weitere Informationen → Trotzdem ausführen*,
  oder vorher Rechtsklick auf die Datei → *Eigenschaften* → *Zulassen*.
- **projekt-cockpit.html** – Browser-Version (Edge/Chrome), läuft überall, nur ohne direktes Öffnen lokaler Dateien.

## Deine Daten
Alles liegt in der Excel-Datei, die du im Programm wählst (z. B. auf deinem Netzlaufwerk) – lesbar und bearbeitbar auch ohne das Cockpit.
Das Programm sendet nichts ins Internet. Einstellungen und tägliche Sicherungskopien: `%APPDATA%\ProjektCockpit\`.

## Mit Python starten (statt exe)
```
py -m pip install --user -r requirements.txt
py app\cockpit.py
```

## Aufbau
| Pfad | Inhalt |
|---|---|
| `web/index.html` | Oberfläche und Logik (läuft im Programm und im Browser) |
| `web/xlsx.mini.min.js` | SheetJS – Excel lesen/schreiben |
| `app/cockpit.py`, `app/windialogs.py` | Desktop-Kern (pywebview): Links öffnen, Dateidialoge, Excel-Datei, Sicherungen |
| `tools/` | Build-Hilfen (Browser-Version, Versionsnummer) |
| `VERSION` | aktuelle Versionsnummer – ein neues Release entsteht, wenn sie erhöht wird |

## Mitmachen
Fehler gefunden, Idee? Gern als **Issue** hier im Repository.

## Lizenz
MIT – siehe [`LICENSE.txt`](LICENSE.txt). Kostenlos, auch gewerblich, ohne Gewähr.
Komponenten Dritter: [`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md).
© 2026 MedConcept UG (haftungsbeschränkt)
