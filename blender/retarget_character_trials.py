"""Bake Ningling's manual trials onto a target's own humanoid rig.

Run with a clean target .blend and -- qinglan / jingxing. No mesh edits.
These are separate drafts, not approved replacements for automatic motions.
"""
from pathlib import Path
import sys
import bpy, addon_utils

ROOT=Path(__file__).resolve().parents[1]
name=sys.argv[sys.argv.index('--')+1]
assert name in ('qinglan','jingxing')
addon_utils.enable('bl_ext.user_default.vrm')
arm=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
scene=bpy.context.scene
for suffix,source in [('cupped_greeting','ningling_cupped_greeting.vrma'),
                      ('wave_draft','ningling_wave_draft.vrma'),
                      ('farewell_wave_candidate','ningling_farewell_wave_candidate.vrma'),
                      ('clap_draft','applaud_monk_adjusted.vrma')]:
    arm.animation_data_clear()
    for b in arm.pose.bones:
        b.matrix_basis.identity()
    bpy.ops.import_scene.vrma(filepath=str(ROOT/'frontend/public/motions'/source),armature_object_name=arm.name)
    start,end=map(int,arm.animation_data.action.frame_range)
    scene.frame_start=start;scene.frame_end=end
    bpy.ops.object.select_all(action='DESELECT');arm.select_set(True)
    bpy.context.view_layer.objects.active=arm
    bpy.ops.object.mode_set(mode='POSE');bpy.ops.pose.select_all(action='SELECT')
    bpy.ops.nla.bake(frame_start=start,frame_end=end,step=1,only_selected=True,visual_keying=True,
                     clear_constraints=False,use_current_action=True,bake_types={'POSE'})
    bpy.ops.object.mode_set(mode='OBJECT')
    scene.frame_set((start+end)//2)
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/f'blender/{name}-{suffix}.blend'))
    out=ROOT/f'frontend/public/motions/{name}_{suffix}.vrma'
    bpy.ops.export_scene.vrma(filepath=str(out),armature_object_name=arm.name)
    print('CHARACTER_TRIAL_EXPORTED',name,suffix,start,end,scene.render.fps)
