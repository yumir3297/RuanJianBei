"""Bake the palm-aligned clap on Qinglan's own proportions."""
from pathlib import Path
script=Path(__file__).with_name('adjust_monk_clap.py')
source=script.read_text().replace('NinglingClap_', 'QinglanClap_')
source=source.replace('ningling-clap-adjusted.blend','qinglan-clap-adjusted.blend')
source=source.replace('applaud_monk_adjusted.vrma','applaud_qinglan_adjusted.vrma')
source=source.replace('NINGLING_EXPORT','QINGLAN_EXPORT')
# Let wide cuffs hang below the hands instead of shrinking the garment to fit.
source=source.replace('weight * 0.075', 'weight * 0.125')
exec(compile(source,str(script),'exec'))
