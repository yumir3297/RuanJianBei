"""Author a manual-preview greeting for Ningling; keep existing gestures intact."""
from pathlib import Path
from math import radians, sin, pi, sqrt, atan2
import bpy, addon_utils
from mathutils import Vector, Matrix, Quaternion

ROOT = Path(__file__).resolve().parents[1]
addon_utils.enable('bl_ext.user_default.vrm')
scene = bpy.context.scene
arm = next(o for o in scene.objects if o.type == 'ARMATURE')
hb = arm.data.vrm_addon_extension.vrm1.humanoid.human_bones
def bone(n): return arm.pose.bones[getattr(hb, n).node.bone_name]
def world(n): return arm.matrix_world @ bone(n).matrix

# Build a hand orientation from its actual finger landmarks, not assumed axes.
wrist = world('right_hand')
finger = (world('right_middle_proximal').translation-wrist.translation).normalized()
across = (world('right_index_proximal').translation-world('right_little_proximal').translation).normalized()
normal = finger.cross(across).normalized()
across = normal.cross(finger).normalized()
source_basis = Matrix((finger, across, normal)).transposed()
target_basis = Matrix((Vector((0,0,1)), Vector((1,0,0)), Vector((0,1,0)))).transposed()
upright = (target_basis @ source_basis.transposed()).to_quaternion() @ wrist.to_quaternion()
finger_open = {
    bone('right_'+digit+'_'+joint).name: bone('right_'+digit+'_'+joint).matrix_basis.to_quaternion()
    for digit in ('index','middle','ring','little')
    for joint in ('proximal','intermediate','distal')
}
bpy.ops.import_scene.vrma(filepath=str(ROOT/'frontend/public/motions/open_clapping.vrma'),armature_object_name=arm.name)
scene.frame_set(1); bpy.context.view_layer.update()
rest = {b.name:b.matrix_basis.copy() for b in arm.pose.bones}
start_hand = world('right_hand').copy()
arm.animation_data_clear()
scene.render.fps = 30
scene.frame_start, scene.frame_end = 1, 91
keys = [(1,0,0),(10,.14,0),(24,.88,-5),(32,1,-9),(43,1,9),(53,1,-7),(63,1,5),(69,.94,0),(81,.30,0),(91,0,0)]
upper_rest = world('right_upper_arm').copy()
lower_rest = world('right_lower_arm').copy()
shoulder = upper_rest.translation.copy()
upper_length = (lower_rest.translation-shoulder).length
lower_length = (start_hand.translation-lower_rest.translation).length
rest_axis = (start_hand.translation-shoulder).normalized()
rest_bend = lower_rest.translation-shoulder
rest_bend = (rest_bend-rest_axis*rest_bend.dot(rest_axis)).normalized()
rest_normal = (lower_rest.translation-shoulder).cross(start_hand.translation-lower_rest.translation).normalized()

def basis(direction, normal):
    direction = direction.normalized()
    normal = (normal-direction*normal.dot(direction)).normalized()
    return Matrix((direction,normal.cross(direction),normal)).transposed()

upper_basis = basis(lower_rest.translation-shoulder,rest_normal)
lower_basis = basis(start_hand.translation-lower_rest.translation,rest_normal)
def orient(name, original, original_basis, direction, normal):
    q = (basis(direction,normal) @ original_basis.transposed()).to_quaternion() @ original.to_quaternion()
    current = world(name)
    bone(name).matrix = arm.matrix_world.inverted() @ Matrix.LocRotScale(current.translation,q,current.to_scale())
    bpy.context.view_layer.update()

previous_quaternions = {}
max_wrist_angle = 0
final_axis = (Vector((-.34,-.15,1.34))-shoulder).normalized()
final_transport = rest_axis.rotation_difference(final_axis) @ rest_bend
preferred = Vector((-.6,-.15,-1)).normalized()
final_bend = (preferred-final_axis*preferred.dot(final_axis)).normalized()
final_twist = atan2(final_axis.dot(final_transport.cross(final_bend)),final_transport.dot(final_bend))
for frame in range(1,92):
    before = max(k for k in keys if k[0] <= frame)
    after = min(k for k in keys if k[0] >= frame)
    t = (frame-before[0])/(after[0]-before[0]) if after[0] != before[0] else 0
    t = t*t*(3-2*t)
    weight = before[1]+(after[1]-before[1])*t
    angle = before[2]+(after[2]-before[2])*t
    for b in arm.pose.bones:
        b.rotation_mode = 'QUATERNION'
        b.matrix_basis = rest[b.name]
        if b.name in finger_open:
            b.rotation_quaternion = rest[b.name].to_quaternion().slerp(finger_open[b.name],weight*.9)
    bpy.context.view_layer.update()
    # Solve the elbow position geometrically: no uncalibrated IK pole angle.
    wrist_pos = start_hand.translation.lerp(Vector((-.34,-.15,1.34)),weight)
    wrist_pos.y -= .025*sin(pi*weight)
    axis = (wrist_pos-shoulder).normalized()
    distance = (wrist_pos-shoulder).length
    assert abs(upper_length-lower_length)+.001 < distance < upper_length+lower_length-.001
    transported = rest_axis.rotation_difference(axis) @ rest_bend
    bend = Quaternion(axis,final_twist*weight) @ transported
    along = (upper_length**2-lower_length**2+distance**2)/(2*distance)
    elbow = shoulder+axis*along+bend*sqrt(max(0,upper_length**2-along**2))
    upper_direction = elbow-shoulder
    forearm = wrist_pos-elbow
    normal = upper_direction.cross(forearm).normalized()
    orient('right_upper_arm',upper_rest,upper_basis,upper_direction,normal)
    orient('right_lower_arm',lower_rest,lower_basis,forearm,normal)
    # Keep the hand aligned with the forearm; only a small lateral wave is added.
    hand_direction = Quaternion((0,1,0),radians(angle)) @ forearm.normalized()
    desired_normal = Vector((0,1,0))
    hand_q = (basis(hand_direction,desired_normal) @ source_basis.transposed()).to_quaternion() @ wrist.to_quaternion()
    inherited_hand = world('right_hand').to_quaternion()
    hand_q = inherited_hand.slerp(hand_q,weight)
    current = world('right_hand')
    bone('right_hand').matrix = arm.matrix_world.inverted() @ Matrix.LocRotScale(current.translation,hand_q,current.to_scale())
    bpy.context.view_layer.update()
    max_wrist_angle = max(max_wrist_angle,forearm.angle(hand_direction))
    for b in arm.pose.bones:
        # Finger opening uses this model's original pose, not guessed axes.
        q = b.rotation_quaternion
        if b.name in previous_quaternions and q.dot(previous_quaternions[b.name]) < 0:
            q.negate()
        previous_quaternions[b.name] = q.copy()
        b.keyframe_insert('location',frame=frame)
        b.keyframe_insert('rotation_quaternion',frame=frame)
print('Maximum authored hand deviation (degrees):',max_wrist_angle*180/pi)
scene.frame_set(43)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/ningling-wave-draft.blend'))
bpy.ops.export_scene.vrma(filepath=str(ROOT/'frontend/public/motions/ningling_wave_draft.vrma'),armature_object_name=arm.name)
