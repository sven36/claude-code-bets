from __future__ import print_function
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET
p=Path(r'C:\Users\dd\Documents\PowerShell\Claude_Code_Best_源码分享_模板版_30min.pptx')
ns={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
with ZipFile(str(p)) as z:
    pres=ET.fromstring(z.read('ppt/presentation.xml'))
    sz=pres.find('p:sldSz',ns)
    print('slide size', sz.attrib if sz is not None else None)
    for i in [2,3]:
        xml=z.read('ppt/slides/slide%d.xml'%i)
        root=ET.fromstring(xml)
        pics=root.findall('.//p:pic',ns)
        sps=root.findall('.//p:sp',ns)
        graphicframes=root.findall('.//p:graphicFrame',ns)
        print('slide',i,'bytes',len(xml),'pics',len(pics),'shapes',len(sps),'graphicFrames',len(graphicframes))
        bg=root.find('.//p:cSld/p:bg',ns)
        print('  has bg', bg is not None)
        spTree=root.find('.//p:spTree',ns)
        for child in list(spTree)[:12]:
            tag=child.tag.split('}')[-1]
            name=''
            cnv=child.find('.//p:cNvPr',ns)
            if cnv is not None: name=cnv.attrib.get('name','')
            xfrm=child.find('.//a:xfrm',ns)
            coords=''
            if xfrm is not None:
                off=xfrm.find('a:off',ns); ext=xfrm.find('a:ext',ns)
                if off is not None and ext is not None: coords=str((off.attrib,ext.attrib))
            print(' ',tag,name,coords)
        relpath='ppt/slides/_rels/slide%d.xml.rels'%i
        if relpath in z.namelist():
            print('  rels')
            relroot=ET.fromstring(z.read(relpath))
            for rel in relroot:
                print('   ',rel.attrib)
