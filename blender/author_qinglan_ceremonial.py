"""Qinglan's Hanfu-appropriate low gestures: waist salute and bow farewell.

Both gestures keep the wrists at or below chest height so the wide cuffs hang
naturally instead of folding into cylinders. Run against hanfu.blend.
"""
from pathlib import Path
from math import radians, cos, pi
import bpy, addon_utils
from mathutils import Quaternion, Vector

ROOT = Path(__file__).resolve().parents[1]
addon_utils.enable('bl_ext.user_default.vrm')
arm = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
hb = arm.data.vrm_addon_extension.vrm1.humanoid.human_bones
def bone(n): return arm.pose.bones[getattr(hb, n).node.bone_name]

# Relaxed reference pose from the licensed open clap (frame 1 only).
bpy.ops.import_scene.vrma(filepath=str(ROOT / 'frontend/public/motions/open_clapping.vrma'), armature_object_name=arm.name)
scene = bpy.context.scene
scene.frame_set(1)
bpy.context.view_layer.update()
rest = {b.name: b.rotation_quaternion.copy() for b in arm.pose.bones}
rest_hands = {s: (arm.matrix_world @ bone(s + '_hand').matrix).copy() for s in ('left', 'right')}
shoulder = (arm.matrix_world @ bone('left_upper_arm').matrix).translation.copy()
arm.animation_data_clear()
scene.render.fps = 30


def smooth(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def weight_at(keys, frame):
    before = max(k for k in keys if k[0] <= frame)
    after = min(k for k in keys if k[0] >= frame)
    if after[0] == before[0]:
        return before[1]
    return before[1] + (after[1] - before[1]) * smooth((frame - before[0]) / (after[0] - before[0]))


def author(suffix, last_frame, arm_keys, bow_keys, bow_angles, targets, hand_turns, yaw_angles=()):
    helpers = []
    for side, sign in (('left', 1), ('right', -1)):
        target = bpy.data.objects.new(f'Qinglan_{suffix}_{side}', None)
        scene.collection.objects.link(target)
        helpers.append(target)
        target.rotation_mode = 'QUATERNION'
        rotation = Quaternion((0, 1, 0), radians(hand_turns[side])) @ rest_hands[side].to_quaternion()
        start, end = targets[side]
        for frame in range(1, last_frame + 1):
            weight = weight_at(arm_keys, frame)
            target.location = start.lerp(end, weight)
            target.rotation_quaternion = rest_hands[side].to_quaternion().slerp(rotation, weight)
            target.keyframe_insert('location', frame=frame)
            target.keyframe_insert('rotation_quaternion', frame=frame)
        ik = bone(side + '_lower_arm').constraints.new('IK')
        ik.target = target
        ik.chain_count = 2
        ik.use_stretch = False
        copy = bone(side + '_hand').constraints.new('COPY_ROTATION')
        copy.target = target
        copy.owner_space = 'WORLD'
        copy.target_space = 'WORLD'
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.select_all(action='SELECT')
    bpy.ops.nla.bake(frame_start=1, frame_end=last_frame, step=1, only_selected=True,
                     visual_keying=True, clear_constraints=True, use_current_action=True,
                     bake_types={'POSE'})
    bpy.ops.object.mode_set(mode='OBJECT')
    for helper in helpers:
        bpy.data.objects.remove(helper, do_unlink=True)
    # Bow after baking so chest/neck/head do not fight the arm solve.
    for frame in range(1, last_frame + 1):
        scene.frame_set(frame)
        bow = weight_at(bow_keys, frame)
        yaw = weight_at(bow_keys, frame)
        for name, angle in bow_angles:
            b = bone(name)
            b.rotation_mode = 'QUATERNION'
            b.rotation_quaternion = (rest[b.name]
                                     @ Quaternion((1, 0, 0), radians(angle) * bow)
                                     @ Quaternion((0, 1, 0), radians(dict(yaw_angles).get(name, 0)) * yaw))
            b.keyframe_insert('rotation_quaternion', frame=frame)
    scene.frame_start, scene.frame_end = 1, last_frame
    scene.frame_set((last_frame + 1) // 2)
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / f'blender/qinglan-{suffix}.blend'))
    bpy.ops.export_scene.vrma(filepath=str(ROOT / f'frontend/public/motions/qinglan_{suffix}.vrma'),
                              armature_object_name=arm.name)
    print('QINGLAN_EXPORT', suffix, last_frame, scene.render.fps)


# Greeting: a small side-turn welcome with a shallow nod. Arms stay at rest so
# the bell cuffs keep hanging; the turn and gaze carry the greeting instead.
author('salute_greeting', 101,
       [(1, 0), (14, .08), (34, .95), (44, 1), (74, 1), (90, .35), (101, 0)],
       [(1, 0), (30, .4), (46, 1), (74, 1), (92, 0), (101, 0)],
       [('chest', 4), ('neck', 2), ('head', 3)],
       {s: (rest_hands[s].translation.copy(), rest_hands[s].translation.copy()) for s in ('left', 'right')},
       {'left': 0, 'right': 0},
       [('chest', 9), ('neck', 3), ('head', 5)])

# Bow farewell (欠身礼): relaxed hands, small forward shift, deeper bow.
bow_target = {s: rest_hands[s].translation + Vector((0, -.025, -.01)) for s in ('left', 'right')}
author('bow_farewell', 91,
       [(1, 0), (12, .05), (30, .9), (40, 1), (62, 1), (78, .4), (91, 0)],
       [(1, 0), (18, .3), (38, 1), (60, 1), (80, 0), (91, 0)],
       [('chest', 9), ('neck', 4), ('head', 5)],
       {s: (rest_hands[s].translation.copy(), bow_target[s]) for s in ('left', 'right')},
       {'left': 0, 'right': 0})
