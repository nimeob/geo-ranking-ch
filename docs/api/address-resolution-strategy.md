# Address Resolution Strategy (BL-20.3.a)

## Ziel
Robuste, provider-neutrale Input-Pipeline für Adresse → Entity-Resolution mit stabilen IDs als Basis für spätere Map-/Mobile-Flows (BL-30.x).

## Pipeline (v1)
1. **Input-Normalisierung**
   - Funktion: `normalize_address_query_input(...)`
   - Vereinheitlicht Whitespace, Trenner (`;`, `|`, Zeilenumbrüche) und Kommaformat.
2. **Adress-Parsing**
   - Funktion: `parse_query_parts(...)`
   - Extrahiert `street`, `house_number`, `postal_code`, `city` aus normalisiertem Input.
   - Unterstützt typische Hausnummer-Muster wie `10a/2`.
3. **Kandidatenauflösung**
   - `search_candidates` → `build_candidate_list` → `hydrate_candidates`
   - Provider-Pfad bleibt austauschbar; die Parsing-/Normalisierungslogik ist nicht an einen einzelnen Provider gekoppelt.
4. **Stabile Identifier-Ableitung**
   - Funktion: `derive_resolution_identifiers(...)`
   - Liefert additiv:
     - `entity_id` (Priorität: `ch:egid:*` → `ch:egrid:*` → `ch:feature:*`)
     - `location_id` (Priorität: `ch:lv95:*:*` → `ch:wgs84:*:*`)
     - `resolution_id` (`ch:resolution:v1:<hash>`)

## API-Ausgabe (additiv, non-breaking)
Die IDs werden in `result.data.entity.ids` ergänzt (`entity_id`, `location_id`, `resolution_id`).
Zusätzlich enthält `result.data.modules.match.resolution` die Pipeline-Metadaten (`pipeline_version`, `strategy`, `provider_path`, selektierter Ursprung).

## Edge-Case-Abdeckung
Abgesichert in `tests/test_core.py`:
- Separator-/Abkürzungs-Normalisierung (`St. Leonhard-Str. 39 ; 9000 ...`)
- Hausnummern mit Suffix/Ranges (`10A/2`)
- Fallback-Pfade bei fehlenden offiziellen IDs (Feature/WGS84)

## Forward-Compatibility
- **Additive Felder:** keine Breaking-Änderung bestehender Payload-Pfade.
- **Provider-neutral:** Input-Normalisierung und ID-Ableitung bleiben unabhängig vom konkreten Geocoder.
- **Reusability:** IDs sind für kanalübergreifende Flows (API/GUI/Mobile/Map) wiederverwendbar.
