"""Blender-authored, manual-only exhibit/reminder trials on target rigs.

Run a clean male-guide.blend -- jingxing, 林二女.blend -- ningling,
or hanfu.blend -- qinglan (exhibit only; keep the wide cuffs low).
Reuses the geometric arm solver, not the wave poses or oscillation. No mesh edits.
"""
from pathlib import Path
import sys
import bpy

ROOT = Path(__file__).resolve().parents[1]
name = sys.argv[sys.argv.index('--') + 1]
assert name in ('jingxing', 'ningling', 'qinglan')
clean_file = bpy.data.filepath
script = ROOT / 'blender/author_ningling_wave.py'
base = script.read_text()
old_schedule = '[(1,0,0),(10,.14,0),(24,.88,-5),(32,1,-9),(43,1,9),(53,1,-7),(63,1,5),(69,.94,0),(81,.30,0),(91,0,0)]'
for suffix in (('exhibit_draft',) if name == 'qinglan' else ('exhibit_draft', 'remind_draft')):
    source = base
    if suffix == 'exhibit_draft':
        # Open beside the torso; fingers follow the forearm, palm obliquely up.
        offset = {'jingxing': 'Vector((-.24, -.22, -.27))',
                  'qinglan': 'Vector((-.22, -.12, -.34))'}.get(name, 'Vector((-.20, -.24, -.25))')
        normal = 'Vector((0, -.2, 1))' if name == 'qinglan' else 'Vector((0, -.35, 1))'
        schedule = '[(1,0,0),(10,.03,0),(30,.85,0),(42,1,0),(62,1,0),(76,.55,0),(91,0,0)]'
    else:
        # Low open palm, held once without lateral wagging or finger pointing.
        offset = 'Vector((-.16, -.22, -.18))' if name == 'jingxing' else 'Vector((-.14, -.20, -.19))'
        normal = 'Vector((0, -1, .15))'
        schedule = '[(1,0,0),(12,.04,0),(28,.92,0),(36,1,0),(55,1,0),(70,.65,0),(91,0,0)]'
    target = f'(shoulder + {offset} * ((upper_length + lower_length) / .50))'
    assert base.count('Vector((-.34,-.15,1.34))') == 2
    assert old_schedule in base
    source = source.replace('Vector((-.34,-.15,1.34))', target)
    source = source.replace(old_schedule, schedule)
    source = source.replace('desired_normal = Vector((0,1,0))', f'desired_normal = {normal}')
    source = source.replace('ningling-wave-draft.blend', f'{name}-{suffix}.blend')
    source = source.replace('ningling_wave_draft.vrma', f'{name}_{suffix}.vrma')
    exec(compile(source, str(script), 'exec'))
    bpy.ops.wm.open_mainfile(filepath=clean_file)
