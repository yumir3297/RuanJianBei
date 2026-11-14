"""Design a gentle cupped-hands greeting for Ningling; run with 林二女.blend."""
from pathlib import Path
from math import radians, sin, pi
import bpy, addon_utils
from mathutils import Quaternion, Vector

ROOT = Path(__file__).resolve().parents[1]
addon_utils.enable('bl_ext.user_default.vrm')
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
hb = arm.data.vrm_addon_extension.vrm1.humanoid.human_bones
def bone(name): return arm.pose.bones[getattr(hb, name).node.bone_name]
# Use the licensed open clap only as a neutral finger/arm reference, not its timing.
bpy.ops.import_scene.vrma(filepath=str(ROOT/'frontend/public/motions/open_clapping.vrma'), armature_object_name=arm.name)
scene = bpy.context.scene
scene.frame_set(1); bpy.context.view_layer.update()
rest = {b.name: b.rotation_quaternion.copy() for b in arm.pose.bones}
rest_hands = {s: (arm.matrix_world @ bone(s+'_hand').matrix).copy() for s in ('left','right')}
scene.frame_set(20); bpy.context.view_layer.update()
pose = {b.name: b.rotation_quaternion.copy() for b in arm.pose.bones}
hand_rot = {s: (arm.matrix_world @ bone(s+'_hand').matrix).to_quaternion() for s in ('left','right')}
arm.animation_data_clear()
scene.render.fps = 30
scene.frame_start, scene.frame_end = 1, 111
# Preserve the previously accepted baked pose from frame 42 onward exactly.
previous_path = ROOT/'blender/ningling-cupped-greeting-before-lift-fix.blend'
accepted = {}
first_version_wrists = {}
with bpy.data.libraries.load(str(previous_path), link=False) as (source, loaded):
    loaded.objects = source.objects
previous_arm = next(o for o in loaded.objects if o and o.type == 'ARMATURE')
scene.collection.objects.link(previous_arm)
for frame in range(1,112):
    scene.frame_set(frame); bpy.context.view_layer.update()
    accepted[frame] = {b.name: b.matrix_basis.copy() for b in previous_arm.pose.bones}
    first_version_wrists[frame] = {
        side: (previous_arm.matrix_world @ previous_arm.pose.bones[bone(side+'_hand').name].matrix).copy()
        for side in ('left','right')
    }
bpy.data.objects.remove(previous_arm, do_unlink=True)
schedule = [(1,0,0),(10,0.05,0),(30,0.85,0),(42,1,0),(57,1,1),(72,1,0.3),(82,0.9,0),(103,0.05,0),(111,0,0)]
helpers=[]
for frame, weight, bow in schedule:
    for b in arm.pose.bones:
        b.rotation_mode='QUATERNION'
        # Keep pelvis and legs at the neutral standing pose.
        upper = any(getattr(hb,n).node.bone_name == b.name for n in ['spine','chest','upper_chest','neck','head','left_shoulder','right_shoulder','left_upper_arm','right_upper_arm','left_lower_arm','right_lower_arm','left_hand','right_hand']) or any(x in b.name.lower() for x in ['finger','thumb','index','middle','ring','little'])
        b.rotation_quaternion = rest[b.name].slerp(pose[b.name], weight if upper else 0)
        b.keyframe_insert('rotation_quaternion',frame=frame)
    for name, angle in [('chest',5),('neck',2),('head',3)]:
        b=bone(name)
        b.rotation_quaternion = rest[b.name] @ Quaternion((1,0,0),radians(angle)*bow)
        b.keyframe_insert('rotation_quaternion',frame=frame)
for side, sign in [('left',1),('right',-1)]:
    obj=bpy.data.objects.new('GreetingWrist_'+side,None);scene.collection.objects.link(obj);helpers.append(obj)
    obj.rotation_mode='QUATERNION'
    # Fingers point diagonally inward. Left hand rests just ahead of the right.
    rotation=Quaternion((0,1,0),radians(-sign*65)) @ hand_rot[side]
    target=Vector((sign*.065,-.30 + (0 if side=='left' else .035),1.10 + (0 if side=='left' else -.012)))
    for frame,weight,bow in schedule:
        obj.location=rest_hands[side].translation.lerp(target+Vector((0,-.012*bow,-.015*bow)),weight)
        obj.rotation_quaternion=rest_hands[side].to_quaternion().slerp(rotation,weight)
        obj.keyframe_insert('location',frame=frame);obj.keyframe_insert('rotation_quaternion',frame=frame)
    # First-version relative hand spacing/orientation is retained. Both wrists
    # follow the same small forward arc; do not separate the hands laterally.
    for frame in range(1,43):
        matrix = first_version_wrists[frame][side]
        offset = .045 * sin(pi*(frame-1)/41)**2
        obj.location = matrix.translation + Vector((0,-offset,0))
        obj.rotation_quaternion = matrix.to_quaternion()
        obj.keyframe_insert('location',frame=frame)
        obj.keyframe_insert('rotation_quaternion',frame=frame)
    ik=bone(side+'_lower_arm').constraints.new('IK');ik.target=obj;ik.chain_count=2;ik.use_stretch=False
    c=bone(side+'_hand').constraints.new('COPY_ROTATION');c.target=obj;c.owner_space='WORLD';c.target_space='WORLD'
bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);bpy.context.view_layer.objects.active=arm
bpy.ops.object.mode_set(mode='POSE');bpy.ops.pose.select_all(action='SELECT')
bpy.ops.nla.bake(frame_start=1,frame_end=111,step=1,only_selected=True,visual_keying=True,clear_constraints=True,use_current_action=True,bake_types={'POSE'})
bpy.ops.object.mode_set(mode='OBJECT')
for obj in helpers: bpy.data.objects.remove(obj,do_unlink=True)
for frame, transforms in accepted.items():
    if frame < 42: continue
    scene.frame_set(frame)
    for name, matrix in transforms.items():
        b=arm.pose.bones.get(name)
        if not b: continue
        b.matrix_basis=matrix
        b.keyframe_insert('location',frame=frame)
        b.keyframe_insert('rotation_quaternion',frame=frame)
        b.keyframe_insert('scale',frame=frame)
scene.frame_set(50)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/ningling-cupped-greeting.blend'))
bpy.ops.export_scene.vrma(filepath=str(ROOT/'frontend/public/motions/ningling_cupped_greeting.vrma'),armature_object_name=arm.name)
