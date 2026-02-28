# BL-20.7.r2 — Reproduzierbares Demo-Datenset (CH)

Stand: 2026-02-28  
Bezug: #37

## Ziel

Dieses Datenset macht GTM-/Produktdemos reproduzierbar, obwohl sich Live-Daten im Zeitverlauf ändern können.

Verwendung im Demo-Flow:
- Primärfall + Vergleichsfall(e) direkt aus diesem Katalog wählen
- Erwartungshaltung vor der Live-Abfrage kurz ansagen
- Nach der Abfrage nur die im Katalog definierten Kernaussagen verifizieren

## Demo-Standorte (v1)

> Hinweis: Adressen sind als realistische Demo-Anker gewählt. Erwartete Aussagen sind bewusst als **stabil** vs. **indikativ** markiert.

| ID | Standort (Adresse) | Optionaler Kartenpunkt (WGS84) | Erwartete Kernaussagen | Confidence / Unsicherheit |
|---|---|---|---|---|
| DS-CH-01 | Bahnhofstrasse 1, 8001 Zürich | 47.3720, 8.5390 | **Stabil:** Urbanes Kernzentrum mit hoher Angebotsdichte. **Indikativ:** eher hohe PT-/POI-Erreichbarkeit, tendenziell geringere Quietness. | Confidence: **mittel-hoch**. Unsicherheit: Radius-abhängige POI-Dynamik und Tageszeit-Effekte. |
| DS-CH-02 | Rosenbergstrasse 30, 9000 St. Gallen | 47.4248, 9.3767 | **Stabil:** Stadtnahes Umfeld mit Mischstruktur. **Indikativ:** ausgeglicheneres Profil zwischen Erreichbarkeit und Ruhe als DS-CH-01. | Confidence: **mittel**. Unsicherheit: Mikrolage (Hang/Verkehr) kann Teilindikatoren verschieben. |
| DS-CH-03 | Avenue d'Ouchy 4, 1006 Lausanne | 46.5076, 6.6290 | **Stabil:** Urbanes See-/Zentrumsumfeld. **Indikativ:** hohe Accessibility, gemischtes Family-/Quietness-Signal je nach Mikrozone. | Confidence: **mittel**. Unsicherheit: lokale Dichte-/Nutzungsänderungen nahe Hotspots. |
| DS-CH-04 | Via Somplaz 4, 7500 St. Moritz | 46.4970, 9.8391 | **Stabil:** Alpine/touristische Prägung. **Indikativ:** schwankendere Vitality-/Accessibility-Werte je nach Saison. | Confidence: **mittel**. Unsicherheit: saisonale Effekte (Tourismus, Angebotsdichte). |
| DS-CH-05 | Route de Riddes 87, 1950 Sion | 46.2305, 7.3604 | **Stabil:** Regionales Zentrum mit peri-urbanem Randcharakter. **Indikativ:** tendenziell höherer Auto-/Pendlerfit als Kernstadtlage. | Confidence: **mittel**. Unsicherheit: lokale ÖV-Anbindung und Entwicklungsprojekte. |

## Demo-Skript (Kurz)

1. **Primärfall wählen:** DS-CH-01 (urbaner Referenzfall)
2. **Vergleichsfall wählen:** DS-CH-02 oder DS-CH-05 (Balancing/Fit-Diskussion)
3. **Optionaler Kontrastfall:** DS-CH-04 (saisonaler/alpiner Kontrast)
4. **Pro Fall nur drei Checks:**
   - Quellen-/Explainability-Felder vorhanden (`sources`, `as_of`, `confidence`, `derived_from`)
   - 1-2 erwartete Signale bestätigt (nicht jede Einzelmetrik)
   - Abweichungen als **indikativ** markieren, nicht als Fehler darstellen

## Pflege-/Versionierungsregel

- Änderungen am Datenset nur mit kurzer Begründung (z. B. starke Drift oder bessere Reproduzierbarkeit)
- Neue Versionen als `v2`, `v3`, ... kennzeichnen und in `docs/GO_TO_MARKET_MVP.md` referenzieren
- Demos immer mit Datenset-Version nennen (z. B. „Demo auf Basis DS v1")
