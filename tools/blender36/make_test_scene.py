"""Create a small 4.5-authored test scene used to probe 3.6 compatibility.

Run with the 4.5 arm64 build:
  blender.exe -b --factory-startup --python tools/blender36/make_test_scene.py
"""
import bpy
import sys

# Clean slate.
bpy.ops.wm.read_factory_settings(use_empty=True)

# Cube with a Principled BSDF (4.x v2 socket layout).
mesh = bpy.data.meshes.new("Cube")
obj = bpy.data.objects.new("Cube", mesh)
bpy.context.collection.objects.link(obj)
import bmesh
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=2.0)
bm.to_mesh(mesh)
bm.free()

mat = bpy.data.materials.new("TestMat")
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes.get("Principled BSDF")
if bsdf is not None:
    bsdf.inputs["Base Color"].default_value = (0.8, 0.25, 0.1, 1.0)
    bsdf.inputs["Metallic"].default_value = 0.3
    bsdf.inputs["Roughness"].default_value = 0.35
    for name, value in (
        ("Transmission Weight", 0.6),
        ("Subsurface Weight", 0.2),
        ("IOR", 1.45),
        ("Coat Weight", 0.8),
        ("Sheen Weight", 0.5),
        ("Specular IOR Level", 0.7),
        ("Emission Strength", 0.9),
    ):
        if name in bsdf.inputs:
            bsdf.inputs[name].default_value = value
    bsdf.inputs["Emission Color"].default_value = (0.1, 0.9, 0.2, 1.0)
obj.data.materials.append(mat)

# A geometry-nodes modifier, to see how 3.6 handles 4.x-only node types.
group = bpy.data.node_groups.new("Sq2GN", "GeometryNodeTree")
group.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
group.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
gin = group.nodes.new("NodeGroupInput")
gout = group.nodes.new("NodeGroupOutput")
setpos = group.nodes.new("GeometryNodeSetPosition")
group.links.new(gin.outputs[0], setpos.inputs["Geometry"])
group.links.new(setpos.outputs[0], gout.inputs[0])
mod = obj.modifiers.new("Sq2GN", "NODES")
mod.node_group = group

# A light and a camera so the file looks like a real scene.
light_data = bpy.data.lights.new("Sun", type="SUN")
light_data.energy = 3.0
light = bpy.data.objects.new("Sun", light_data)
light.location = (4.0, -3.0, 6.0)
bpy.context.collection.objects.link(light)

cam_data = bpy.data.cameras.new("Camera")
cam = bpy.data.objects.new("Camera", cam_data)
cam.location = (6.0, -6.0, 4.0)
bpy.context.collection.objects.link(cam)
bpy.context.scene.camera = cam

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE_NEXT" if hasattr(scene, "eevee") else scene.render.engine
scene.view_settings.view_transform = "AgX"

out = sys.argv[-1] if sys.argv[-1].endswith(".blend") else "test45.blend"
bpy.ops.wm.save_as_mainfile(filepath=out, check_existing=False)
print("SAVED", out)
print("VERSION", bpy.app.version_string, bpy.app.version)
if bsdf is not None:
    print("PRINCIPLED_SOCKETS", [s.name for s in bsdf.inputs])
