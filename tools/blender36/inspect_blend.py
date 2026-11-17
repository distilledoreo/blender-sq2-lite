"""Inspect a .blend with whatever Blender is running this script.

Reports what survived a cross-version load: objects, materials, node types and
Principled socket names/values. Used to test 4.5 -> 3.6 file compatibility.
"""
import bpy
import sys


def scalar(v):
    try:
        return tuple(round(float(x), 3) for x in v)
    except TypeError:
        return round(float(v), 3)
    except Exception:
        return repr(v)


blend = bpy.data.filepath
print("=== INSPECT", blend)
print("RUNNING", bpy.app.version_string, bpy.app.version)
print("OBJECTS", [(o.name, o.type) for o in bpy.data.objects])
print("SCENE_CAMERA", bpy.context.scene.camera.name if bpy.context.scene.camera else None)

for mat in bpy.data.materials:
    print("MATERIAL", mat.name, "use_nodes=", mat.use_nodes)
    if not mat.use_nodes or mat.node_tree is None:
        continue
    for node in mat.node_tree.nodes:
        extra = ""
        if node.bl_idname == "ShaderNodeBsdfPrincipled":
            vals = []
            for inp in node.inputs:
                if not inp.is_linked and hasattr(inp, "default_value"):
                    try:
                        vals.append("%s=%s" % (inp.name, scalar(inp.default_value)))
                    except Exception:
                        pass
            extra = " [" + ", ".join(vals) + "]"
        print("  NODE", node.bl_idname, repr(node.name), extra)

print("IMAGES", [i.name for i in bpy.data.images])
print("SCENE_ENGINE", bpy.context.scene.render.engine)
print("VIEW_TRANSFORM", bpy.context.scene.view_settings.view_transform)
for obj in bpy.data.objects:
    for mod in getattr(obj, "modifiers", []):
        detail = ""
        if mod.type == "NODES":
            group = getattr(mod, "node_group", None)
            detail = " group=%s types=%s" % (
                group.name if group else None,
                [n.bl_idname for n in group.nodes] if group else None,
            )
        print("MODIFIER", obj.name, mod.name, mod.type, detail)
for group in bpy.data.node_groups:
    print("NODEGROUP", group.name, [n.bl_idname for n in group.nodes])
print("=== END")
