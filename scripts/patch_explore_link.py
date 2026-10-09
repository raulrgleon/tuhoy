#!/usr/bin/env python3
"""Ghost 5: abre Explore fuera del iframe bloqueado. Sin modificar seguridad remota."""
import pathlib, subprocess, sys, tempfile
MARKER='TUHOY_EXPLORE_EXTERNAL_V1'
OLD='openExploreWindow(){this.config.hostSettings?.forceUpgrade||this.exploreWindowOpen||(this.ensureIframeIsLoaded(),window.location.hash="/explore",this.router.transitionTo("/explore"),this.toggleExploreWindow(!0))}'
NEW='openExploreWindow(){/*'+MARKER+'*/window.open("https://explore.ghost.org/","_blank","noopener,noreferrer")}'
assets=pathlib.Path(sys.argv[1]);files=list(assets.glob('ghost-*.js'))
if any(MARKER in p.read_text() for p in files):
 print('[overrides] Explore externo ya aplicado');sys.exit(0)
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
print('[overrides] Explore abre el directorio en otra pestaña; sin reinicio')
