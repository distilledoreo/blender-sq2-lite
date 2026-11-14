import bpy
import sys
import os

# Usage from bridge.bat:
#   blender -b latest.blend --python export_gltf.py -- out.glb
# Exports meshes/cameras/lights for fast WebGL viewport on SQ2.
# Browser ANGLE->D3D works where Blender desktop GL fails.

argv = sys.argv
try:
    out = argv[argv.index("--") + 1]
except (ValueError, IndexError):
    out = os.path.join(os.path.dirname(bpy.data.filepath), "sq2_preview.glb")

# Apply latest file as-is (headless already handles 5.x files natively on ARM)
bpy.ops.export_scene.gltf(
    filepath=out,
    export_format='GLB',
    use_selection=False,
    export_materials='EXPORT',
    export_cameras=True,
    export_lights=True,
    export_animations=True,
)
print(f"SQ2-BRIDGE exported: {out}")
