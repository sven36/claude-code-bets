from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
p=Path(r'C:\Users\dd\Documents\PowerShell\Claude_Code_0604.pptx')
ns={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
with ZipFile(p) as z:
    print('testzip', z.testzip())
    root=ET.fromstring(z.read('ppt/slides/slide5.xml'))
sp=root.find('.//p:spTree',ns)
print('children', len(list(sp)))
for i,ch in enumerate(list(sp)):
    tag=ch.tag.split('}')[-1]
    cnv=ch.find('.//p:cNvPr',ns); name=cnv.attrib.get('name','') if cnv is not None else ''
    xfrm=ch.find('.//a:xfrm',ns); coords=''
    if xfrm is not None:
        off=xfrm.find('a:off',ns); ext=xfrm.find('a:ext',ns)
        if off is not None and ext is not None: coords=(off.attrib.get('x'),off.attrib.get('y'),ext.attrib.get('cx'),ext.attrib.get('cy'))
    text=''.join(t.text or '' for t in ch.findall('.//a:t',ns))
    print(f'{i:02d} {tag:8s} {name:28s} {coords!s:58s} {text[:120]}')
