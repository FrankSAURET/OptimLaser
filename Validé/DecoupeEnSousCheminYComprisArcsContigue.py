import inkex


class ToSubPaths(inkex.EffectExtension):

    def effect(self):
        # Sélectionner tous les éléments
        for layer in self.svg.getchildren():
            for element in layer.getchildren():
                self.svg.selection.add(element)

        for element in self.svg.selection.filter(inkex.Group, inkex.PathElement, inkex.Circle, inkex.Ellipse, inkex.Rectangle):
            # groups: iterate through descendants
            if isinstance(element, inkex.Group):
                for shape_element in element.descendants().filter(inkex.PathElement, inkex.Circle, inkex.Ellipse, inkex.Rectangle):
                    self.replace_with_subpaths(shape_element)
            else:
                self.replace_with_subpaths(element)

    def replace_with_subpaths(self, element):
        # Thank's to Kaalleen on inkscape forum
        # get info about the position in the svg document
        parent = element.getparent()
        index = parent.index(element)

        # get style and remove fill, the new elements are strokes
        style = element.style
        if not style('stroke', None):
            style['stroke'] = style('fill', None)
        style['fill'] = 'none'

        # path
        path = element.path.to_non_shorthand()

        # generate new elements from sub paths
        for start, end in zip(path[:-1], path[1:]):
            if isinstance(end, inkex.paths.ZoneClose):
                end = inkex.paths.Line(path[0].x, path[0].y)
            start = start.end_point(None, None)
            start = inkex.paths.Move(start.x, start.y)

            segment_path = inkex.Path([start, end])

            new_element = inkex.PathElement(d=str(segment_path),
                                            style=str(style),
                                            transform=str(element.transform))
            parent.insert(index, new_element)
        # remove the original element
        parent.remove(element)

if __name__ == '__main__':
    ToSubPaths().run()
