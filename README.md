# Flare Bench

Physically based lens flares from the lens, the camera and the lights you tag, running live in the browser.

**Open it:** https://x14halo.github.io/flare-bench/

Flare Bench is a prototype exploring what a production lens-flare tool for animated features could look like:
realistic by default, quick to direct, and driven by real shot data rather than hand-placed elements.

## What it does

- **Tagged flare lights.** Add lights by type (sun, HMI, tungsten, practicals, flame, LED, sodium and more). Each one
  flares according to its real brightness, size and colour, with a per-light flare gain in stops for art direction.
- **Screen flares.** Load an HDR or EXR plate and its bright areas (fire, glints, untagged practicals) flare on their own.
  Tagged lights are held out automatically, so nothing flares twice.
- **Real lens behaviour.** Pick a lens family (clean modern, large-format, warm character, vintage, classic and modern
  anamorphic, zoom). Ghosts are ray traced through a lens model, and the star comes from the iris shape. Veiling glare,
  streaks and haze all react to the T-stop, focal length, focus and light position.
- **Camera data.** Import a camera and its tagged lights from 3D (focal length, T-stop, focus distance, light
  positions and gains) as JSON. `houdini/flare_bench_export.py` is a starting-point exporter for Houdini.
- **Before/after wipe**, a **present mode** (press `P`), and **Share a look**, which saves every setting plus the plate to one file.

## Plates

Use `.exr` or `.hdr` files for full dynamic range. JPG and PNG load too, but they're clipped. A 2:1 image loads as a
lat-long panorama you can pan and tilt around. Free HDRIs from [Poly Haven](https://polyhaven.com/hdris) work well.

## Import format

```json
{
  "camera": { "focal_mm": 32, "fstop": 4, "focus_m": 3.5, "lens": "cooke" },
  "lights": [
    { "name": "key_spot", "type": "hmi", "ndc": [0.72, 0.64], "distance_m": 12,
      "kelvin": 5600, "flare_gain_stops": 0 }
  ]
}
```

`ndc` runs 0–1 from the bottom left of frame, and values outside that range place a light off frame. Up to 4 lights are imported.

## Background

The ray-traced ghosts follow Hullin et al., *Physically-Based Real-Time Lens Flare Rendering* (SIGGRAPH 2011).
Aperture diffraction follows Ritschel et al., *Temporal Glare* (2009). The tagged-light workflow follows
Animal Logic's *Physical Based Lens Flare Rendering in The LEGO Movie 2* (DigiPro 2019).

Runs entirely in the browser with WebGL2 and needs no install. EXR loading uses three.js's EXRLoader, served from a CDN.
Prototype built with Claude.
