"""Recompute palm-center contact on each target rig instead of retargeting it."""
from pathlib import Path
import sys

name = sys.argv[sys.argv.index('--') + 1]
assert name in ('qinglan', 'jingxing')
script = Path(__file__).with_name('adjust_monk_clap.py')
source = script.read_text()
source = source.replace('NinglingClap_', name + 'Clap_')
source = source.replace('ningling-clap-adjusted.blend', f'{name}-clap-contact-trial.blend')
source = source.replace('applaud_monk_adjusted.vrma', f'{name}_clap_draft.vrma')
source = source.replace('NINGLING_EXPORT', name.upper() + '_CLAP_EXPORT')
if name == 'qinglan':
    source = source.replace('weight * 0.075', 'weight * 0.125')
else:
    source = source.replace('weight * 0.075', 'weight * 0.095')
exec(compile(source, str(script), 'exec'))
