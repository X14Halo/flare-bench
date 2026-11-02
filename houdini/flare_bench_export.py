"""
Flare Bench export (Houdini Python): the shot camera and the tagged flare lights, per frame, as the small block of
data a Flare node in Nuke would read from the render's EXR header.

Two ways to run it:
  * Solaris / USD (the pipeline way): reads the USD stage of a LOP node. Lights are tagged with attributes on the
    light prim (or the same names as primvars:flare:*), which any light asset can carry:
        flare:enable   bool    on = this light makes a flare (fill and cheat lights stay untagged)
        flare:type     token   a Flare Bench source type: sun, led (car headlight), sodium (streetlight),
                               followspot (stage spot), filament (bare bulb), flashlight, xenon, dedo, mirror
        flare:gain     float   extra flare in stops (0 = as bright as the light really is)
        flare:kelvin   float   optional colour temperature
    Distances come out in metres whatever the stage's units, from the stage's metersPerUnit.
  * /obj (older scenes): the same names as spare parameters on light objects (flare, flare_type, flare_gain,
    flare_kelvin). Set METERS_PER_UNIT to your scene's units (0.01 for centimetres).

Where the data goes:
  * write_json(): a .json file. For the prototype, drop it onto the Flare Bench frame.
  * write_exr_metadata(): into the rendered EXR's own header (attribute "flare/shot", a JSON string), so the data
    travels with the frames and the Nuke node needs no side files. This version rewrites the file with OpenImageIO
    after the render; in production the renderer's EXR driver would write the same attribute while rendering, which
    your pipeline TD wires once on the render product.

Untested sketch: check attribute and parameter names against your studio's camera and light assets.
"""
import json
import math

import hou

# ----------------------------------------------------------------------------------------------------------------------
# shared

ESSENTIAL = ('sun', 'led', 'sodium', 'followspot', 'filament', 'flashlight', 'xenon', 'dedo', 'mirror')


def _project(p_cam, focal_mm, hap_mm, vap_mm):
    """Camera-space point (camera looks down -Z) -> NDC 0-1 across the image. None if behind the camera."""
    depth = -p_cam[2]
    if depth <= 1e-6:
        return None
    return [round(0.5 + (p_cam[0] / depth) * focal_mm / hap_mm, 5),
            round(0.5 + (p_cam[1] / depth) * focal_mm / vap_mm, 5)]


def _light_entry(name, ftype, ndc, dist_m, kelvin, gain):
    if ftype not in ESSENTIAL:
        ftype = 'sun' if dist_m is None else 'filament'
    d = {'name': name, 'type': ftype, 'ndc': ndc, 'flare_gain_stops': float(gain or 0.0)}
    if dist_m is not None:
        d['distance_m'] = round(dist_m, 3)
    if kelvin:
        d['kelvin'] = float(kelvin)
    return d


# ----------------------------------------------------------------------------------------------------------------------
# Solaris / USD

def export_stage(lop_path, camera_path, frame=None):
    """Camera and tagged lights from a LOP node's stage at a frame (default: the current frame)."""
    from pxr import Usd, UsdGeom, UsdLux, Gf

    frame = hou.frame() if frame is None else frame
    stage = hou.node(lop_path).stage()
    t = Usd.TimeCode(frame)
    mpu = UsdGeom.GetStageMetersPerUnit(stage) or 1.0

    cam_prim = stage.GetPrimAtPath(camera_path)
    cam = UsdGeom.Camera(cam_prim)
    focal = cam.GetFocalLengthAttr().Get(t)                     # USD stores these in mm-like "tenths of a unit";
    hap = cam.GetHorizontalApertureAttr().Get(t)                # Houdini writes them in mm, which is all the ratio needs
    vap = cam.GetVerticalApertureAttr().Get(t)
    fstop = cam.GetFStopAttr().Get(t) or 0.0
    focus = cam.GetFocusDistanceAttr().Get(t) or 0.0
    cam_xf = UsdGeom.Xformable(cam_prim).ComputeLocalToWorldTransform(t)
    to_cam = cam_xf.GetInverse()

    def tag(prim, name, default=None):
        for attr_name in ('flare:' + name, 'primvars:flare:' + name):
            a = prim.GetAttribute(attr_name)
            if a and a.HasAuthoredValue():
                return a.Get(t)
        return default

    lights = []
    for prim in stage.Traverse():
        if not prim.HasAPI(UsdLux.LightAPI) and not prim.IsA(UsdLux.BoundableLightBase) and not prim.IsA(UsdLux.NonboundableLightBase):
            continue
        if not tag(prim, 'enable', False):
            continue
        xf = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(t)
        if prim.IsA(UsdLux.DistantLight):
            # a light at infinity: only its direction matters; it shines down its -Z, so the sun sits along +Z
            d_world = xf.TransformDir(Gf.Vec3d(0, 0, 1))
            d_cam = to_cam.TransformDir(d_world)
            ndc, dist_m = _project(d_cam, focal, hap, vap), None
        else:
            p_cam = to_cam.Transform(xf.ExtractTranslation())
            ndc, dist_m = _project(p_cam, focal, hap, vap), p_cam.GetLength() * mpu
        if ndc is None:
            continue                                            # behind the camera
        lights.append(_light_entry(prim.GetName(), tag(prim, 'type', None), ndc, dist_m,
                                   tag(prim, 'kelvin', None), tag(prim, 'gain', 0.0)))

    return {
        'camera': {'focal_mm': focal, 'fstop': fstop, 'focus_m': focus * mpu if focus else None,
                   'aspect': hap / vap if vap else None, 'frame': frame, 'path': camera_path},
        'lights': lights,
    }


# ----------------------------------------------------------------------------------------------------------------------
# /obj

METERS_PER_UNIT = 1.0      # 0.01 if the scene is in centimetres


def export_obj(camera_path='/obj/cam1', frame=None):
    frame = hou.frame() if frame is None else frame
    cam = hou.node(camera_path)
    ev = lambda node, name, default=None: node.parm(name).evalAtFrame(frame) if node.parm(name) is not None else default
    focal = ev(cam, 'focal')                                     # mm (assumes focalunits = mm)
    hap = ev(cam, 'aperture')                                    # horizontal film aperture, mm
    aspect = float(ev(cam, 'resx')) / ev(cam, 'resy') * ev(cam, 'aspect', 1.0)
    vap = hap / aspect
    to_cam = cam.worldTransformAtTime(hou.frameToTime(frame)).inverted()

    lights = []
    for node in hou.node('/obj').allSubChildren():
        if not ev(node, 'flare', 0):
            continue
        xf = node.worldTransformAtTime(hou.frameToTime(frame))
        if ev(node, 'light_type', '') == 'distant':
            d_cam = (hou.Vector4(0, 0, 1, 0) * xf * to_cam)
            ndc, dist_m = _project(d_cam, focal, hap, vap), None
        else:
            p_cam = hou.Vector3(xf.extractTranslates()) * to_cam
            ndc, dist_m = _project(p_cam, focal, hap, vap), p_cam.length() * METERS_PER_UNIT
        if ndc is None:
            continue
        lights.append(_light_entry(node.name(), ev(node, 'flare_type', None), ndc, dist_m,
                                   ev(node, 'flare_kelvin', None), ev(node, 'flare_gain', 0.0)))

    focus = ev(cam, 'focus', None)
    return {
        'camera': {'focal_mm': focal, 'fstop': ev(cam, 'fstop', 2.8), 'focus_m': focus * METERS_PER_UNIT if focus else None,
                   'aspect': aspect, 'frame': frame, 'path': camera_path},
        'lights': lights,
    }


# ----------------------------------------------------------------------------------------------------------------------
# writers

def write_json(data, path=None):
    path = path or hou.expandString('$HIP/flare_bench_shot.json')
    with open(path, 'w') as f:
        json.dump(data, f, indent=1)
    print('Flare Bench: wrote %d tagged light(s) to %s' % (len(data['lights']), path))
    return path


def write_exr_metadata(exr_path, data, key='flare/shot'):
    """Store the frame's camera and tagged lights in the EXR header as one JSON string attribute.
    Nuke shows it as exr/flare/shot in the Read node's metadata."""
    import OpenImageIO as oiio
    buf = oiio.ImageBuf(exr_path)
    buf.specmod().attribute(key, json.dumps(data, separators=(',', ':')))
    tmp = exr_path + '.tmp.exr'
    if not buf.write(tmp):
        raise RuntimeError(buf.geterror())
    import os
    os.replace(tmp, exr_path)


def export_range(start, end, exr_pattern, lop_path=None, camera_path='/cameras/shotcam'):
    """After a render: tag every frame's EXR with that frame's data. exr_pattern uses $F4-style padding,
    e.g. '/path/beauty.$F4.exr'."""
    for f in range(int(start), int(end) + 1):
        data = export_stage(lop_path, camera_path, f) if lop_path else export_obj(camera_path, f)
        write_exr_metadata(hou.expandStringAtFrame(exr_pattern, f), data)


if __name__ == '__main__':
    # Solaris: write_json(export_stage('/stage/OUT', '/cameras/shotcam'))
    write_json(export_obj('/obj/cam1'))
