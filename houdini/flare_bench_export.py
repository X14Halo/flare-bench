"""
Flare Bench export (Houdini Python): writes the shot camera and the tagged flare lights at the current frame to a
JSON file that Flare Bench's "Import camera & lights" reads.

How lights are tagged: add spare parameters to any light you want to flare (fill and cheat lights stay untagged):
    flare            toggle   on = this light makes a flare
    flare_type       string   a Flare Bench source type: sun, hmi, tungsten, practical, filament, flame, led, sodium, ...
    flare_gain       float    extra flare in stops (0 = as bright as the light really is)
    flare_kelvin     float    optional colour temperature

Usage: set CAMERA and OUT below, then run it from the Python Shell or a shelf tool.
Untested sketch: check parameter names against your studio's camera and light HDAs.
"""
import json
import hou

CAMERA = '/obj/cam1'
OUT = hou.expandString('$HIP/flare_bench_shot.json')

cam = hou.node(CAMERA)
focal = cam.evalParm('focal')                      # mm (assumes focalunits = mm)
aperture = cam.evalParm('aperture')                # horizontal film aperture, mm
resx, resy = cam.evalParm('resx'), cam.evalParm('resy')
aspect = float(resx) / resy * cam.evalParm('aspect')
to_cam = cam.worldTransform().inverted()

def parm(node, name, default=None):
    p = node.parm(name)
    return p.eval() if p is not None else default

lights = []
for node in hou.node('/obj').allSubChildren():
    if not parm(node, 'flare', 0):
        continue
    p = hou.Vector3(node.worldTransform().extractTranslates()) * to_cam    # camera space, camera looks down -Z
    depth = -p[2]
    if depth <= 1e-4:
        continue                                                            # behind the camera
    ndc_x = 0.5 + (p[0] / depth) * (focal / aperture)
    ndc_y = 0.5 + (p[1] / depth) * (focal / aperture) * aspect
    lights.append({
        'name': node.name(),
        'type': parm(node, 'flare_type', 'hmi') or 'hmi',
        'ndc': [round(ndc_x, 5), round(ndc_y, 5)],                          # may be outside 0-1 for off-frame lights
        'distance_m': round(p.length(), 3),
        'kelvin': parm(node, 'flare_kelvin', None),
        'flare_gain_stops': parm(node, 'flare_gain', 0.0),
    })

data = {
    'camera': {
        'focal_mm': focal,
        'fstop': parm(cam, 'fstop', 2.8),
        'focus_m': parm(cam, 'focus', None),
        'aspect': aspect,
        'frame': hou.frame(),
    },
    'lights': lights,
}
with open(OUT, 'w') as f:
    json.dump(data, f, indent=1)
print('Flare Bench: wrote %d tagged light(s) to %s' % (len(lights), OUT))
