# Notices

LZ Brief © 2026 RBM Global. All rights reserved.

The tool contains no third-party code. Everything — coordinate parsing, the MGRS/UTM
implementation, the tile engine, the renderer and the map picker — is original and
inlined in `index.html`. There are no bundled libraries and no CDN dependencies.

## Imagery and data services

| Service | Used for | Terms |
|---|---|---|
| **Esri World Imagery** (`server.arcgisonline.com`) | The high-resolution base | Esri Master Agreement / basemap terms. Attribution: Esri, Maxar/Vantor, Earthstar Geographics |
| **Esri Wayback** (`wayback.maptiles.arcgis.com`) | Historical captures for the season comparison | As above |
| **Esri World Imagery metadata** | Capture date, resolution, sensor | As above |
| **Esri World Boundaries and Places** | Place names on the wide panel and the hybrid picker | As above |
| **Esri World Transportation** | Roads on the hybrid picker | As above |
| **SRTM** via OpenTopoData / Open-Elevation | Elevation and local slope | SRTM is public domain (NASA/USGS). The API hosts are free public services with rate limits and no availability guarantee |
| **Mapbox Satellite** | Second look on the comparison sheet; optional primary base | Mapbox ToS. Requires an account token. Publishes no capture date, and is never labelled with one |

Satellite imagery displayed by the tool remains the property of its providers.
Imagery is fetched live and, other than the browser's own cache, is not stored.

## Licensing position — open

The Esri endpoints used are the open basemap endpoints. For **commercial and
operational** use Esri expects an ArcGIS Location Platform account and an API key
against `ibasemaps-api.arcgis.com`. The free tier is generous and costs nothing to set
up. Both versions have a slot for the key — `ESRI_KEY` at the top of `index.html`, and
`--esri-key` on the CLI — and setting it switches the endpoint.

Redistributing Maxar/Vantor-derived imagery outside your own organisation is a separate
question from using it. Worth confirming against Esri's terms before client work
depends on this.

**Bing Maps** was considered and rejected: Microsoft has retired it for new customers
and the enterprise API ends in 2028.
