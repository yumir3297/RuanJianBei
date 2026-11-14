"""Gently trim outer cuffs from the original, retaining the wide-sleeve silhouette."""
from pathlib import Path
import json, struct

ROOT = Path(__file__).resolve().parents[1]
src = ROOT/'blender/vrm/hanfu.vrm'
dst = ROOT/'frontend/public/models/hanfu-small-sleeves.vrm'
raw = src.read_bytes()
chunks=[]; offset=12
while offset < len(raw):
    size,kind=struct.unpack_from('<II',raw,offset)
    chunks.append((kind,raw[offset+8:offset+8+size])); offset+=8+size
doc=json.loads(chunks[0][1]); data=bytearray(chunks[1][1])
# Quantized mesh coordinates are decoded through the root inverse-bind matrix.
body_node=next(n for n in doc['nodes'] if n.get('name')=='Body')
ib=doc['accessors'][doc['skins'][body_node['skin']]['inverseBindMatrices']]
bv=doc['bufferViews'][ib['bufferView']]
matrix=struct.unpack_from('<16f',data,bv.get('byteOffset',0)+ib.get('byteOffset',0))
decode_scale=[matrix[0],matrix[5],matrix[10]]; decode_offset=list(matrix[12:15])
changed=0; visited=set(); before=[]; after=[]
for mesh in doc['meshes']:
    for primitive in mesh['primitives']:
        material=doc['materials'][primitive.get('material',0)].get('name','')
        if 'N00_007_01_Tops' not in material: continue
        aid=primitive['attributes']['POSITION']
        if aid in visited: continue
        visited.add(aid)
        a=doc['accessors'][aid]; view=doc['bufferViews'][a['bufferView']]
        assert a['componentType']==5122 and a['type']=='VEC3' and a['normalized']
        base=view.get('byteOffset',0)+a.get('byteOffset',0); stride=view.get('byteStride',6)
        points=[]
        for i in range(a['count']):
            encoded=struct.unpack_from('<hhh',data,base+i*stride)
            x,y,z=[encoded[k]/32767*decode_scale[k]+decode_offset[k] for k in range(3)]
            if abs(x)>.43 and y>.95:
                # Keep the shoulder/elbow and hanging sleeve body untouched.
                # Retain 60% of the outer cuff cross-section, with a long blend
                # into the untouched elbow so the bell shape remains visible.
                t=min(1,max(0,(abs(x)-.43)/.13)); t=t*t*(3-2*t)
                scale=1-.40*t
                nx=(1 if x>0 else -1)*(.54+(abs(x)-.54)*.40) if abs(x)>.54 else x
                ny=1.284+(y-1.284)*scale
                nz=-.025+(z+.025)*scale
                before.append((x,y,z)); after.append((nx,ny,nz))
                x,y,z=nx,ny,nz;changed+=1
                encoded=tuple(round((p-decode_offset[k])/decode_scale[k]*32767) for k,p in enumerate((x,y,z)))
                assert all(-32767<=n<=32767 for n in encoded)
                struct.pack_into('<hhh',data,base+i*stride,*encoded)
            points.append(encoded)
        a['min']=[min(p[k] for p in points) for k in range(3)]
        a['max']=[max(p[k] for p in points) for k in range(3)]
assert changed>100
j=json.dumps(doc,separators=(',',':'),ensure_ascii=False).encode();j+=b' '*((-len(j))%4)
data+=b'\0'*((-len(data))%4)
out=struct.pack('<III',0x46546c67,2,12+8+len(j)+8+len(data))+struct.pack('<II',len(j),0x4e4f534a)+j+struct.pack('<II',len(data),0x004e4942)+data
dst.write_bytes(out)
print('SLEEVE_VERTICES_CHANGED',changed)
print('MAX_SLEEVE_HALFSPAN_BEFORE_AFTER',max(abs(p[0]) for p in before),max(abs(p[0]) for p in after))
print('VRM_EXTENSIONS_PRESERVED',list(doc.get('extensions',{})))
print('OUTPUT',dst)
