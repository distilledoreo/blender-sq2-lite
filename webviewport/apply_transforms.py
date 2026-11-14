import bpy
import json
import sys

# Usage (headless, native ARM, works on SQ2):
#   blender -b latest.blend --python apply_transforms.py -- sq2_transforms.json converted.blend
#
# Applies simple object transforms edited in view.html back to the .blend.
# Matches by object name. Bones: matches pose bones by name if object is armature.
# Character skeletal ANIMATION clips are previewed in web; to bake them back,
# export glTF from web is lossy - instead re-animate in Blender using these
# transforms as staging reference, or bake action in Blender (see below).

argv = sys.argv
args = argv[argv.index("--") + 1:]
src_json = args[0] if len(args) > 0 else "sq2_transforms.json"
dst_blend = args[1] if len(args) > 1 else "//sq2_applied.blend"

with open(src_json, "r") as f:
    data = json.load(f)

applied, missing = 0, []
for name, tr in data.items():
    loc = tr.get("location")
    rot = tr.get("rotation_euler")
    scl = tr.get("scale")
    ob = bpy.data.objects.get(name)
    if ob:
        if loc: ob.location = loc
        if rot: ob.rotation_mode = 'XYZ'; ob.rotation_euler = rot
        if scl: ob.scale = scl
        applied += 1
        continue
    # try pose bone: "Armature/BoneName" or bare bone name
    found = False
    for arm in [o for o in bpy.data.objects if o.type == 'ARMATURE']:
        bone_name = name.split("/")[-1]
        if bone_name in arm.pose.bones:
            pb = arm.pose.bones[bone_name]
            if loc: pb.location = loc
            if rot: pb.rotation_mode = 'XYZ'; pb.rotation_euler = rot
            if scl: pb.scale = scl
            # auto-key it so it survives as animation:
            # pb.keyframe_insert(data_path="location")
            applied += 1
            found = True
            break
    if not found:
        missing.append(name)

print(f"SQ2-BRIDGE applied {applied} transforms, missing {len(missing)}: {missing[:10]}")
bpy.ops.wm.save_as_mainfile(filepath=dst_blend)
print(f"Saved {dst_blend}")
