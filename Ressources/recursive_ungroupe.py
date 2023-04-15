import inkex


class RecursiveUngroup(inkex.Effect):
    def __init__(self):
        inkex.Effect.__init__(self)

    def recursively_ungroup(self, node):
        if node.tag == inkex.addNS("g", "svg"):
            for child in node:
                self.recursively_ungroup(child)
            parent = node.getparent()
            if parent is not None:
                index = parent.index(node)
                parent[index:index + 1] = node

    def effect(self):
        for node in self.document.getroot().xpath("//svg:g", namespaces=inkex.NSS):
            self.recursively_ungroup(node)


if __name__ == '__main__':
    RecursiveUngroup().run()
