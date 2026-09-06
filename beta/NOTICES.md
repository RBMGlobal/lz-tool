# Notices

LZ Brief © 2026 RBM Global. All rights reserved.

`index.html` contains no third-party code. Everything in it — coordinate parsing, the
MGRS/UTM implementation, the tile engine, the Sentinel-2 GeoTIFF reader, the renderer,
the ZIP writer and the map picker — is original. There are no CDN dependencies.

The one bundled library is the OCR engine behind **Read a screen photo**, self-hosted in
`vendor/` and loaded only when that button is used:

| File | What | Licence |
|---|---|---|
| `vendor/tesseract.min.js`, `vendor/worker.min.js` | Tesseract.js 5.1.1 (naptha/tesseract.js) | Apache-2.0 |
| `vendor/tesseract-core-simd-lstm.wasm.js` | tesseract.js-core 5.1.1 — Tesseract OCR compiled to WebAssembly | Apache-2.0 |
| `vendor/eng.traineddata.gz` | Tesseract English model, tessdata 4.0.0 (best, integer) | Apache-2.0 |

The Apache-2.0 notice is `vendor/tesseract.min.js.LICENSE.txt`.

Everything around the engine — finding the data strip, straightening the picture,
cutting out the text lines, repairing the misreads and deciding which line is the
target — is original, and mirrored in `cli/osdfind.py` and `cli/lzocr.py`. The CLI side
of that uses **numpy** and **scipy** (both BSD-3-Clause); the browser side uses neither.

OCR runs entirely on the device; the photo is never uploaded anywhere.

**No webfont is bundled or fetched.** The page names Montserrat and Avenir Next
in its font stack and falls back to the platform default; nothing is downloaded,
so the tool still opens with no signal.

The RBM Global identity — the emblem, the wordmark and the colour palette — is
RBM Global's own property, reproduced here from `Full RBM CI.pdf` and used in
accordance with those guidelines. The emblem in `index.html` is an inline SVG
traced from `Icon.pdf`, at the CI's specified ring opacities.

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
| **Copernicus Sentinel-2 L2A** via Earth Search STAC (Element 84) and the `sentinel-cogs` AWS Open Data bucket | The LATEST PASS image — recent, dated, 10 m | Copernicus Sentinel data is free, full and open, commercial use included, under the [Copernicus Sentinel Data Terms](https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice). Attribution required and carried on every panel and page: *Contains modified Copernicus Sentinel data [year]*. Earth Search and the AWS bucket are free public services with no availability guarantee |

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

**Google Maps satellite** was considered and rejected: the Map Tiles API terms (§3.2.3(a))
forbid exporting or resharing Google Maps Content outside the Services, which is the whole
purpose of this tool, and the undocumented `mt1.google.com` tile server is not a licensed
service at all. Sentinel-2 fills the "another look" role legitimately, and with dates.

**Bing Maps** was considered and rejected: Microsoft has retired it for new customers
and the enterprise API ends in 2028.
