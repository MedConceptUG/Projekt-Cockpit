# Code signing policy

Free code signing provided by [SignPath.io](https://about.signpath.io/), certificate by [SignPath Foundation](https://signpath.org/).

## What is signed
- `Projekt-Cockpit.exe` (Windows desktop program) published under [Releases](https://github.com/MedConceptUG/projekt-cockpit/releases).

Only artifacts built by the public GitHub Actions workflow in this repository (`.github/workflows/build.yml`) from the public source code are submitted for signing. The private signing key is held by SignPath; it is never stored in this repository or on a developer machine.

## Team roles
- **Authors / Committers:** [MedConceptUG](https://github.com/MedConceptUG)
- **Reviewers:** [MedConceptUG](https://github.com/MedConceptUG) – all external contributions (pull requests) are reviewed before merging.
- **Approvers:** [MedConceptUG](https://github.com/MedConceptUG) – every signing request is approved manually.

## Privacy
This program will not transfer any information to other networked systems unless specifically requested by the user or the person installing or operating it.
All project data stays in the Excel file chosen by the user and in local settings on the user's computer.

## Distribution
Official downloads are only available from the [GitHub Releases](https://github.com/MedConceptUG/projekt-cockpit/releases) of this repository.

---

**Deutsch (Kurzfassung):** Die Windows-Programmdatei wird kostenlos über SignPath.io mit einem Zertifikat der SignPath Foundation signiert. Signiert werden nur Dateien, die der öffentliche GitHub-Build aus dem öffentlichen Quellcode erzeugt; jede Signatur wird manuell freigegeben. Das Programm überträgt keine Daten an andere Systeme, außer der Nutzer veranlasst es ausdrücklich.
