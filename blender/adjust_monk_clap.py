"""Blender: run against 林二女.blend to adapt the upstream clap for Ningling."""
from pathlib import Path
import bpy
import addon_utils
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
addon_utils.enable('bl_ext.user_default.vrm')
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
bpy.ops.import_scene.vrma(filepath=str(ROOT / 'frontend/public/motions/open_clapping.vrma'), armature_object_name=arm.name)
hb = arm.data.vrm_addon_extension.vrm1.humanoid.human_bones
def bone(name):
    return arm.pose.bones[getattr(hb, name).node.bone_name]

scene = bpy.context.scene
start, end = map(int, arm.animation_data.action.frame_range)
scene.frame_start, scene.frame_end = start, end
samples = {}
for frame in range(start, end + 1):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    samples[frame] = {}
    palm_offsets = {}
    original_palms = []
    for side in ('left', 'right'):
        hand = bone(side + '_hand')
        matrix = arm.matrix_world @ hand.matrix
        position = matrix.translation.copy()
        middle = arm.matrix_world @ bone(side + '_middle_proximal').head
        palm_offsets[side] = (middle - position) * 0.6
        original_palms.append(position + palm_offsets[side])
        # Smooth activation based on source wrist elevation, preserving entry/exit.
        weight = max(0, min(1, (position.z - 0.88) / 0.25))
        weight = weight * weight * (3 - 2 * weight)
        position.z -= weight * (0.12 + max(0, position.z - 1.20) * 0.65)
        position.y -= weight * 0.075
        sign = 1 if side == 'left' else -1
        # Keep wrists apart; fingers project inward from the wrists to clap.
        position.x = (1 - weight) * position.x + weight * sign * (0.025 + abs(position.x) * 0.60)
        samples[frame][side] = (position, matrix.to_quaternion())
    # Match palm centers, not wrists: source proportions otherwise leave an air gap.
    left, right = samples[frame]['left'][0], samples[frame]['right'][0]
    center = (left + palm_offsets['left'] + right + palm_offsets['right']) * 0.5
    gap = max(0.022, min(0.18, ((original_palms[0] - original_palms[1]).length - 0.045) * 1.1))
    activation = max(0, min(1, (frame - 7) / 5, (70 - frame) / 5))
    activation = activation * activation * (3 - 2 * activation)
    for side, sign in [('left', 1), ('right', -1)]:
        target = center + Vector((sign * gap * 0.5, 0, 0)) - palm_offsets[side]
        position, rotation = samples[frame][side]
        samples[frame][side] = (position.lerp(target, activation), rotation)

helpers = []
for side in ('left', 'right'):
    target = bpy.data.objects.new('NinglingClap_' + side, None)
    scene.collection.objects.link(target)
    helpers.append(target)
    target.rotation_mode = 'QUATERNION'
    for frame, values in samples.items():
        target.location, target.rotation_quaternion = values[side]
        target.keyframe_insert('location', frame=frame)
        target.keyframe_insert('rotation_quaternion', frame=frame)
    ik = bone(side + '_lower_arm').constraints.new('IK')
    ik.target = target
    ik.chain_count = 2
    ik.use_stretch = False
    rotation = bone(side + '_hand').constraints.new('COPY_ROTATION')
    rotation.target = target
    rotation.owner_space = 'WORLD'
    rotation.target_space = 'WORLD'

bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')
bpy.ops.pose.select_all(action='SELECT')
bpy.ops.nla.bake(frame_start=start, frame_end=end, step=1, only_selected=True,
                 visual_keying=True, clear_constraints=True, use_current_action=True, bake_types={'POSE'})
bpy.ops.object.mode_set(mode='OBJECT')
for helper in helpers:
    bpy.data.objects.remove(helper, do_unlink=True)
scene.frame_set(30)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'blender/ningling-clap-adjusted.blend'))
bpy.ops.export_scene.vrma(filepath=str(ROOT / 'frontend/public/motions/applaud_monk_adjusted.vrma'), armature_object_name=arm.name)
print('NINGLING_EXPORT', start, end, scene.render.fps)
