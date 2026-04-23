"""Kompatibilitäts-Brücke für ``src.api.web_service``.

Der Legacy-HTTP-Service liegt weiterhin in ``src/api/web_service.py``,
während parallel ein neues Paket unter ``src/api/web_service/`` aufgebaut wird.

Viele bestehende Tests/Importe erwarten beim Import von
``src.api.web_service`` den Legacy-Inhalt. Diese Brücke führt deshalb die
Legacy-Datei *im Namespace dieses Paketmoduls* aus.

Vorteil gegenüber bloßem Re-Export:
- Funktions-Globals bleiben auf diesem Modulobjekt,
  sodass ``mock.patch("src.api.web_service.<name>")`` wie erwartet wirkt.
"""

from __future__ import annotations

from pathlib import Path


_LEGACY_MODULE_PATH = Path(__file__).resolve().parent.parent / "web_service.py"

# Den Legacy-Code direkt in dieses Modul laden, damit bestehende Monkeypatches
# (z. B. in den Unit-Tests) weiterhin aufgelöste Namen im selben Modulraum
# überschreiben können.
exec(compile(_LEGACY_MODULE_PATH.read_text(encoding="utf-8"), str(_LEGACY_MODULE_PATH), "exec"), globals())
