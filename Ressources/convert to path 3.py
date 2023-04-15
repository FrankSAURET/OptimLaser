import inkex
import simplestyle
import cubicsuperpath
import xml.etree.ElementTree as ET


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

    root = elem.getroottree().getroot()
    d = ET.SubElement(root, inkex.addNS('path', 'svg'))
    p = cubicsuperpath.parsePath(inkex.paths.get_path_d(elem))
    d.text = cubicsuperpath.formatPath(p)
    elem.getparent().remove(elem)


class ConvertToPath(inkex.Effect):
    def __init__(self):
        inkex.Effect.__init__(self)

    def effect(self):
        for node in self.document.xpath('//*[not(self::svg:path)]', namespaces=inkex.NSS):
            convert_to_path(node)


if __name__ == '__main__':
    e = ConvertToPath()
    e.affect()
