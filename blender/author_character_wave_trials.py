"""Author target-proportioned wave trials on a clean character rig.

Unlike rotation retargeting, solve each elbow/wrist on the target skeleton and
use that character's own open-finger landmarks. No garment geometry changes.
Run hanfu.blend -- qinglan or male-guide.blend -- jingxing.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
name = sys.argv[sys.argv.index('--') + 1]
assert name in ('qinglan', 'jingxing')
script = ROOT / 'blender/author_ningling_wave.py'
base = script.read_text()
for suffix in ('wave_draft', 'farewell_wave_candidate'):
    source = base
    # Shoulder-relative targets accommodate stature instead of importing
    # Ningling's absolute wrist positions or normalized arm rotations.
    if name == 'qinglan':
        offset = 'Vector((-.10, -.25, -.10))'
        amplitude = .65 if suffix == 'farewell_wave_candidate' else .8
    else:
        offset = 'Vector((-.12, -.22, -.04))'
        amplitude = 1.35 if suffix == 'farewell_wave_candidate' else 1.0
    target = f'(shoulder + {offset} * ((upper_length + lower_length) / .50))'
    source = source.replace('Vector((-.34,-.15,1.34))', target)
    if suffix == 'farewell_wave_candidate':
        source = source.replace(
            '[(1,0,0),(10,.14,0),(24,.88,-5),(32,1,-9),(43,1,9),(53,1,-7),(63,1,5),(69,.94,0),(81,.30,0),(91,0,0)]',
            '[(1,0,0),(12,.06,0),(30,1,-4),(42,1,7),(55,1,-6),(65,1,3),(72,.94,0),(85,.16,0),(91,0,0)]')
    source = source.replace('radians(angle)) @ forearm.normalized()',
                            f'radians(angle * {amplitude})) @ forearm.normalized()')
    source = source.replace('ningling-wave-draft.blend', f'{name}-{suffix}-authored.blend')
    source = source.replace('ningling_wave_draft.vrma', f'{name}_{suffix}.vrma')
    # Restore the clean target for each pass: reference finger landmarks must
    # not be measured on the final pose left by the preceding action.
    import bpy
    clean_file = bpy.data.filepath
    exec(compile(source, str(script), 'exec'))
    bpy.ops.wm.open_mainfile(filepath=clean_file)
