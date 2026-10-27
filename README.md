# Flare Bench

Physically based lens flares from the lens, the camera and the lights you tag, running live in the browser.

**Open it:** https://x14halo.github.io/flare-bench/

Flare Bench is a prototype exploring what a production lens-flare tool for animated features could look like:
realistic by default, quick to direct, and driven by real shot data rather than hand-placed elements.

## What it does

- **Tagged flare lights.** A short list of the lights that turn up in an animated feature and really flare: sun, car
  headlight, streetlight, stage spotlight, bare bulb and flashlight, plus a torch, a small spot or a mirror bounce aimed
  into the lens from just off frame. Each one flares according to its real brightness, size and colour, with a
  per-light flare gain in stops for art direction.
- **Real lens behaviour.** Pick a lens family (clean modern, large-format, warm character, vintage, classic and modern
  anamorphic, zoom). Ghosts are ray traced through a lens model, and the star comes from the iris shape. Veiling glare,
  streaks and haze all react to the T-stop, focal length, focus and light position. It opens on Large-format modern
  (ARRI Signature Prime class, Roger Deakins' choice for *1917*) with a subtle flare amount and clean front glass.
- **Made for comp.** Turn off **Sources** under the frame to see the flare alone, as it would go over a render, and
  **Handles** to hide the light markers. **+ Add light** (or `A`) opens the light picker; `Delete` removes a light.
- **Before/after wipe**, a **present mode** (press `P`), and **Share a look**, which saves every setting to one file.

The panel's **How it works → Under the hood** section explains the optics in detail: the lens prescriptions, ghost
paths, GPU ray tracing, coatings, spectral rendering, diffraction and glare.

## In progress

The page also has screen flares from HDR/EXR plates and a camera-and-lights import from 3D, but both are switched off in
the panel for now (`FEATURE_PLATES` in `index.html`). `houdini/flare_bench_export.py` is a starting-point exporter
for that import.

## Background

The ray-traced ghosts follow Hullin et al., *Physically-Based Real-Time Lens Flare Rendering* (SIGGRAPH 2011).
Aperture diffraction follows Ritschel et al., *Temporal Glare* (2009). The tagged-light workflow follows
Animal Logic's *Physical Based Lens Flare Rendering in The LEGO Movie 2* (DigiPro 2019).

Runs entirely in the browser with WebGL2 and needs no install. EXR loading uses three.js's EXRLoader, served from a CDN.
Prototype built with Claude.
