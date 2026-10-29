"""Updated 2026-10-29 · Editable vector diagram for the dataset one-pager."""
from reportlab.graphics.shapes import Drawing, Rect, String, PolyLine, Polygon
from reportlab.lib.colors import HexColor

def module_diagram():
    d = Drawing(515, 174)
    teal, gold, ink = '#008681', '#B68416', '#173B3A'
    def text(x,y,s,size=8,color=ink,bold=False):
        d.add(String(x,y,s,fontName='Helvetica-Bold' if bold else 'Helvetica',
                     fontSize=size,fillColor=HexColor(color),textAnchor='middle'))
    def box(x,y,w,h,color):
        d.add(Rect(x,y,w,h,rx=6,ry=6,fillColor=HexColor(color),strokeColor=None))
    def path(points,color,arrow=True):
        d.add(PolyLine(points,strokeColor=HexColor(color),strokeWidth=1.2))
        if arrow:
            x,y=points[-2:]; px,py=points[-4:-2]
            dx,dy=x-px,y-py; norm=(dx*dx+dy*dy)**.5;dx/=norm;dy/=norm
            d.add(Polygon([x,y,x-5*dx+2.3*dy,y-5*dy-2.3*dx,
                           x-5*dx-2.3*dy,y-5*dy+2.3*dx],
                          fillColor=HexColor(color),strokeColor=None))
    box(154,141,207,30,'#DCEDEA')
    text(257.5,159,'MASTER DATASET',9,bold=True)
    text(257.5,148,'Baseline + approved, origin-tagged additions',7.3)
    path([257.5,141,257.5,125],teal,False)
    path([80,125,426,125],teal,False)
    text(112,131,'Published data',7,teal)
    for x,title,lines in [
        (8,'ORACLE',['Evidence + search indexes','Private user context*']),
        (181,'ECOSYSTEM',['Published base','Working records + proposals']),
        (354,'SIMULATION',['Models + inputs','Run outputs / predictions'])]:
        box(x,61,144,51,'#F0F5F4')
        path([x+72,125,x+72,112],teal)
        text(x+72,98,title,8.5,bold=True)
        text(x+72,84,lines[0],7.5)
        text(x+72,72,lines[1],7.5)
        path([x+72,61,x+72,46],gold,False)
    path([80,46,426,46],gold,False)
    path([257.5,46,257.5,33],gold)
    text(127,36,'Proposed changes',7,gold)
    box(177,9,161,24,'#FFF1D4')
    text(257.5,24,"LIOR'S APPROVAL",8,bold=True)
    text(257.5,14,'Exact revision only',7)
    path([338,21,507,21,507,156,361,156],gold)
    text(424,12,'Approved publication',7,gold)
    text(130,1,'*Private context is not shared by default. No direct sibling writes.',6.5)
    return d

if __name__ == '__main__':
    from pathlib import Path
    from reportlab.graphics import renderSVG
    renderSVG.drawToFile(module_diagram(),str(Path(__file__).with_name('meatcode-dataset-modules.svg')))
