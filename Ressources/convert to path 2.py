import inkex
import simplestyle

def convert_to_path(elem):
    if elem.tag == inkex.addNS('path', 'svg'):
        return

    style = simplestyle.parseStyle(elem.attrib.get('style', ''))
    if 'fill' in style:
        del style['fill']
    if 'stroke' in style:
        style['fill'] = style['stroke']
        del style['stroke']
    elem.attrib['style'] = simplestyle.formatStyle(style)

    path_d = inkex.paths.obj_to_path(elem)
    elem.clear()
    elem.attrib['d'] = path_d
    elem.tag = inkex.addNS('path', 'svg')

class ConvertToPath(inkex.Effect):
    def __init__(self):
        inkex.Effect.__init__(self)

    def effect(self):
        for node in self.document.getroot().xpath('//*[not(self::svg:path)]', namespaces=inkex.NSS):
            convert_to_path(node)

if __name__ == '__main__':
    e = ConvertToPath()
    e.affect()
