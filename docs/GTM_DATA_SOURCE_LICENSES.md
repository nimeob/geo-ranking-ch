# BL-20.7.r1 — Lizenzgrenzen für GTM-Artefakte

Stand: 2026-02-26  
Bezug: #36  
Abhängige Quelleninventar-Arbeit: #24 (BL-20.2.a)

## Zweck

Dieses Dokument definiert, welche datenquellenbezogenen Aussagen in GTM-Materialien (Value Proposition, Demo-Storyline, Sales-Messaging) aktuell verwendet werden dürfen.

Ziel: **keine Vermarktungs-Claims ohne dokumentierte Nutzungs- und Attributionsgrundlage**.

## Scope der Prüfung (GTM-Artefakte)

Geprüft wurden die in den GTM-nahen Artefakten explizit genannten Quellen:

- `docs/GO_TO_MARKET_MVP.md`
- `docs/VISION_PRODUCT.md` (Sektion „Datenquellen (Startpunkt)“)

## Lizenz- und Claim-Matrix (MVP)

| Datenquelle | Typische Nutzung im Produkt | Kommerzielle Nutzung | Attribution/Weitergabe | Erlaubter GTM-Claim (MVP) | Status |
|---|---|---|---|---|---|
| **swisstopo / geo.admin.ch** | Geobasis-/Kontextdaten für Standortanalyse, Kartenbezug, Referenzlayer | **Bedingt ja** (gemäß publizierten Nutzungsbedingungen der jeweiligen Datensätze/Services; Datensatz-spezifische Einschränkungen möglich) | Quellenangabe erforderlich; Datensatz-/Service-spezifische Bedingungen prüfen | „Nutzt offizielle CH-Geodatenquellen inkl. swisstopo/geo.admin.ch mit nachvollziehbarer Quellenangabe.“ | ✅ **Freigegeben mit Auflagen** |
| **GWR / BFS-Registerdaten** | Gebäude-/Adressnahe Registerinformationen | **Bedingt ja** (abhängig vom konkreten Datensatz/Export und dessen Bedingungen) | Quellenangabe erforderlich; allfällige Datensatzhinweise übernehmen | „Integriert öffentliche Registerdaten (z. B. GWR) mit dokumentierter Herkunft.“ | ✅ **Freigegeben mit Auflagen** |
| **OpenStreetMap (OSM)** | POI-/Kontextdaten, ergänzende Open-Datenebenen | **Ja, mit ODbL-Auflagen** | OSM-Attribution verpflichtend; ODbL-Anforderungen (insb. bei Datenbank-Weitergabe) beachten | „Ergänzt amtliche Daten um OSM-Daten unter ODbL inkl. erforderlicher Attribution.“ | ✅ **Freigegeben mit Auflagen** |
| **„Weitere öffentliche Quellen“ (unspezifisch)** | Platzhalter für zukünftige Datendomänen (Lärm, Mobilität, Infrastruktur) | **Unklar ohne Einzelfallprüfung** | Nicht pauschal ableitbar | **Nicht verwenden:** keine pauschalen Lizenz-/Nutzbarkeitsclaims für nicht konkret benannte Quellen | ⛔ **Claim nicht verwenden** |

## Verbindliche Guardrails für GTM-Texte

1. Keine Aussage „alle Daten kommerziell frei nutzbar“.
2. Nur konkret benannte Quellen kommunizieren (swisstopo/geo.admin, GWR, OSM).
3. Bei OSM muss Attribution in Demo-/Marketingmaterial sichtbar eingeplant werden.
4. Unspezifische Sammelbegriffe („weitere öffentliche Quellen“) nur technisch, nicht lizenzrechtlich vermarkten.
5. Bei Unsicherheit: Claim streichen und als Follow-up in #24 dokumentieren.

## Referenzen (für Detailprüfung in BL-20.2.a)

- swisstopo/geo.admin Nutzungsbedingungen (Datensatz-/Service-spezifisch)
- OSM Copyright & ODbL: https://www.openstreetmap.org/copyright
- opendata.swiss / BFS-Datensatzbedingungen je Quelle

> Hinweis: Dieses Dokument ist ein **GTM-Claim-Gate** für MVP-Kommunikation. Die vollständige, datensatzgenaue Lizenz-/Nutzungsdokumentation wird in **#24 (BL-20.2.a)** geführt und fortgeschrieben.
