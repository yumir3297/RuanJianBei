"""A restrained farewell nod, retaining relaxed arms and wide sleeves."""
from pathlib import Path
from math import radians, cos, pi
import bpy, addon_utils
from mathutils import Quaternion

ROOT=Path(__file__).resolve().parents[1]
addon_utils.enable('bl_ext.user_default.vrm')
arm=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
hb=arm.data.vrm_addon_extension.vrm1.humanoid.human_bones
def bone(n): return arm.pose.bones[getattr(hb,n).node.bone_name]
bpy.ops.import_scene.vrma(filepath=str(ROOT/'frontend/public/motions/open_clapping.vrma'),armature_object_name=arm.name)
scene=bpy.context.scene
scene.frame_set(1);bpy.context.view_layer.update()
rest={b.name:b.matrix_basis.copy() for b in arm.pose.bones}
arm.animation_data_clear()
scene.render.fps=30;scene.frame_start=1;scene.frame_end=73
keys=[(1,0),(12,0),(30,1),(39,1),(63,0),(73,0)]
for frame in range(1,74):
    before=max(k for k in keys if k[0]<=frame)
    after=min(k for k in keys if k[0]>=frame)
    t=(frame-before[0])/(after[0]-before[0]) if after[0]!=before[0] else 0
    weight=before[1]+(after[1]-before[1])*(1-cos(pi*t))*.5
    for b in arm.pose.bones:
        b.rotation_mode='QUATERNION';b.matrix_basis=rest[b.name]
    for name,angle in [('chest',1.5),('neck',1.5),('head',4)]:
        b=bone(name)
        b.rotation_quaternion=rest[b.name].to_quaternion() @ Quaternion((1,0,0),radians(angle)*weight)
    for b in arm.pose.bones:
        b.keyframe_insert('location',frame=frame)
        b.keyframe_insert('rotation_quaternion',frame=frame)
scene.frame_set(30)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/qinglan-farewell.blend'))
bpy.ops.export_scene.vrma(filepath=str(ROOT/'frontend/public/motions/qinglan_farewell.vrma'),armature_object_name=arm.name)
print('QINGLAN_FAREWELL: 73 frames at 30 fps; arms fixed at relaxed reference; 7 degree total nod')
