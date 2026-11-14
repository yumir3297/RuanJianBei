"""Adapt the MIT Goodbye animation into a restrained one-hand Ningling farewell."""
from pathlib import Path
import bpy, addon_utils
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
addon_utils.enable('bl_ext.user_default.vrm')
arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
hb=arm.data.vrm_addon_extension.vrm1.humanoid.human_bones
def bone(n): return arm.pose.bones[getattr(hb,n).node.bone_name]
bpy.ops.import_scene.vrma(filepath=str(ROOT/'frontend/public/motions/open_clapping.vrma'),armature_object_name=arm.name)
scene=bpy.context.scene
scene.frame_set(1);bpy.context.view_layer.update()
rest={b.name:b.matrix_basis.copy() for b in arm.pose.bones}
arm.animation_data_clear()
bpy.ops.import_scene.vrma(filepath=str(ROOT/'frontend/public/motions/open_goodbye.vrma'),armature_object_name=arm.name)
start,end=map(int,arm.animation_data.action.frame_range)
samples={}
for frame in range(start,end+1):
 scene.frame_set(frame);bpy.context.view_layer.update()
 matrix=arm.matrix_world@bone('right_hand').matrix
 pos=matrix.translation.copy()
 weight=max(0,min(1,(pos.z-.88)/.28));weight=weight*weight*(3-2*weight)
 pos.z-=weight*.055
 pos.y-=weight*.045
 pos.x=-abs(pos.x)
 samples[frame]=(pos,matrix.to_quaternion())
 # Remove the other waving hand and unrelated whole-body sway.
 for name in ['hips','spine','chest','upper_chest','neck','head','left_shoulder','left_upper_arm','left_lower_arm','left_hand']:
  b=bone(name);b.matrix_basis=rest[b.name]
  b.keyframe_insert('location',frame=frame);b.keyframe_insert('rotation_quaternion',frame=frame)
 for name in ['thumb_metacarpal','thumb_proximal','thumb_distal','index_proximal','index_intermediate','index_distal','middle_proximal','middle_intermediate','middle_distal','ring_proximal','ring_intermediate','ring_distal','little_proximal','little_intermediate','little_distal']:
  b=bone('left_'+name);b.matrix_basis=rest[b.name];b.keyframe_insert('rotation_quaternion',frame=frame)
  b=bone('right_'+name)
  b.rotation_quaternion=b.rotation_quaternion.slerp(rest[b.name].to_quaternion(),.22*weight)
  b.keyframe_insert('rotation_quaternion',frame=frame)
target=bpy.data.objects.new('FarewellRightWrist',None);scene.collection.objects.link(target);target.rotation_mode='QUATERNION'
for frame,(pos,rot) in samples.items():
 target.location=pos;target.rotation_quaternion=rot
 target.keyframe_insert('location',frame=frame);target.keyframe_insert('rotation_quaternion',frame=frame)
ik=bone('right_lower_arm').constraints.new('IK');ik.target=target;ik.chain_count=2;ik.use_stretch=False
c=bone('right_hand').constraints.new('COPY_ROTATION');c.target=target;c.owner_space='WORLD';c.target_space='WORLD'
bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);bpy.context.view_layer.objects.active=arm
bpy.ops.object.mode_set(mode='POSE');bpy.ops.pose.select_all(action='SELECT')
bpy.ops.nla.bake(frame_start=start,frame_end=end,step=1,only_selected=True,visual_keying=True,clear_constraints=True,use_current_action=True,bake_types={'POSE'})
bpy.ops.object.mode_set(mode='OBJECT');bpy.data.objects.remove(target,do_unlink=True)
scene.frame_start=start;scene.frame_end=end;scene.frame_set(35)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/ningling-farewell.blend'))
bpy.ops.export_scene.vrma(filepath=str(ROOT/'frontend/public/motions/ningling_farewell.vrma'),armature_object_name=arm.name)
