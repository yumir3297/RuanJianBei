"""Generate separate farewell candidates; do not overwrite accepted gestures.

Run against hanfu.blend or 林二女.blend with -- qinglan / ningling.
Uses the arm solver but a lower wrist position and slower farewell timing.
"""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
name=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'qinglan'
assert name in ('qinglan','ningling')
script=ROOT/'blender/author_ningling_wave.py'
source=script.read_text()
source=source.replace('Vector((-.34,-.15,1.34))','Vector((-.29,-.22,1.23))')
source=source.replace('[(1,0,0),(10,.14,0),(24,.88,-5),(32,1,-9),(43,1,9),(53,1,-7),(63,1,5),(69,.94,0),(81,.30,0),(91,0,0)]',
                      '[(1,0,0),(10,.08,0),(28,1,-4),(39,1,7),(52,1,-6),(64,1,3),(70,.95,0),(84,.18,0),(91,0,0)]')
source=source.replace('ningling-wave-draft.blend',f'{name}-farewell-wave-candidate.blend')
if name == 'ningling':
    # Increase only the hand-direction wave, not the wrist/elbow position path.
    source=source.replace('radians(angle)) @ forearm.normalized()',
                          'radians(angle * 2.2)) @ forearm.normalized()')
source=source.replace('ningling_wave_draft.vrma',f'{name}_farewell_wave_candidate.vrma')
exec(compile(source,str(script),'exec'))
