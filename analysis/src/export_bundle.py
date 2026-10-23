"""Create a full project ZIP and a small repository ZIP beside the project folder."""
from pathlib import Path
import zipfile,json,sys,platform
import pandas as pd
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
env={'python':sys.version.split()[0],'pandas':pd.__version__,'numpy':np.__version__,'platform':platform.system(),
 'dependencies':'requirements.txt; sqlite3 and urllib use the Python standard library'}
(ROOT/'docs/environment.json').write_text(json.dumps(env,indent=2))
files=[p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
for filename,source_only in [('olist-marketplace-intelligence.zip',False),('olist-github-source.zip',True)]:
 target=ROOT.parent/filename
 with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in files:
   relative=p.relative_to(ROOT)
   if source_only and (relative.parts[0]=='data' or relative.as_posix() in ['dashboard/data.js','dashboard/OPEN_DASHBOARD.html']):continue
   z.write(p,ROOT.name+'/'+relative.as_posix())
 with zipfile.ZipFile(target) as z:
  if z.testzip() is not None:raise AssertionError('Archive CRC failure')
 print(filename,round(target.stat().st_size/1e6,2),'MB',flush=True)
