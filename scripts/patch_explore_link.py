#!/usr/bin/env python3
"""Ghost 5: abre Explore fuera del iframe bloqueado. Sin modificar seguridad remota."""
import pathlib, subprocess, sys, tempfile
MARKER='TUHOY_EXPLORE_EXTERNAL_V1'
OLD='openExploreWindow(){this.config.hostSettings?.forceUpgrade||this.exploreWindowOpen||(this.ensureIframeIsLoaded(),window.location.hash="/explore",this.router.transitionTo("/explore"),this.toggleExploreWindow(!0))}'
NEW='openExploreWindow(){/*'+MARKER+'*/window.open("https://explore.ghost.org/","_blank","noopener,noreferrer")}'
assets=pathlib.Path(sys.argv[1]);files=list(assets.glob('ghost-*.js'))
def bust_cache(p):
 index=assets.parent/'index.html'
 original=index.read_text()
 old='assets/'+p.name+'"'
 new='assets/'+p.name+'?tuhoy-explore=1"'
 if old in original:
  backup=index.with_suffix('.html.tuhoy-before-explore')
  if not backup.exists():backup.write_text(original)
  index.write_text(original.replace(old,new))
 elif new not in original:raise SystemExit('Referencia de admin incompatible')
for p in files:
 if MARKER in p.read_text():
  bust_cache(p);print('[overrides] Explore externo ya aplicado');sys.exit(0)
matched=[p for p in files if OLD in p.read_text()]
if len(matched)!=1:raise SystemExit('Versión de Ghost incompatible: Explore no modificado')
p=matched[0];original=p.read_text()
if original.count(OLD)!=1:raise SystemExit('Explore ambiguo: no modificado')
updated=original.replace(OLD,NEW)
with tempfile.NamedTemporaryFile(suffix='.js',mode='w') as tmp:
 tmp.write(updated);tmp.flush();subprocess.run(['node','--check',tmp.name],check=True)
backup=p.with_suffix(p.suffix+'.tuhoy-before-explore')
if not backup.exists():backup.write_text(original)
p.write_text(updated)
bust_cache(p)
print('[overrides] Explore abre el directorio en otra pestaña; sin reinicio')
