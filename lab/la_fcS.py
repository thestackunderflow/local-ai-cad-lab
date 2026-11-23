"""la S check for FreeCAD (freecadcmd, headless): the shown solids of one saved document -> LA_OUT json.
    LA_DOC=after-X.FCStd LA_OUT=after-X.s.json freecadcmd lab/la_fcS.py
A shown solid = a top-level object (a Body, or a Part feature not inside a Body) with Visibility on and a non-empty
solid shape, after a recompute. Per solid: bounding-box dims, volume, solid count, validity."""
import json
import os

import FreeCAD

doc = FreeCAD.openDocument(os.environ['LA_DOC'])
doc.recompute()
out = {'doc': os.path.basename(os.environ['LA_DOC']), 'solids': [], 'objects': []}
for o in doc.Objects:
    shp = getattr(o, 'Shape', None)
    top = o.getParentGeoFeatureGroup() is None
    vis = bool(getattr(o, 'Visibility', True))
    row = {'name': o.Name, 'type': o.TypeId, 'top': top, 'visible': vis,
           'state': list(o.State)}
    if shp is not None and not shp.isNull():
        row['solids'] = len(shp.Solids)
    out['objects'].append(row)
    if top and vis and shp is not None and not shp.isNull() and shp.Solids and not o.TypeId.startswith('App::'):
        b = shp.BoundBox
        out['solids'].append({'name': o.Name, 'type': o.TypeId, 'dims': [round(b.XLength, 4), round(b.YLength, 4),
                              round(b.ZLength, 4)], 'volume': round(shp.Volume, 3), 'n_solids': len(shp.Solids),
                              'valid': shp.isValid()})
json.dump(out, open(os.environ['LA_OUT'], 'w'), indent=1)
print('LAS', out['doc'], json.dumps(out['solids']))
