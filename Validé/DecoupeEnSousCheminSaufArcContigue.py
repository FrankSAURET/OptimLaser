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

        # Supprimer les lignes de longueur nulle
        new_path = [path[0]]
        for i in range(1, len(path)):
            segment = path[i]
            segmentPrev = path[i-1]
            if not isinstance(segmentPrev, inkex.paths.ZoneClose) and not isinstance(segment, inkex.paths.ZoneClose):
                Fin = (segment.x, segment.y)
                Debut = (segmentPrev.x, segmentPrev.y)
            if segment.letter == 'L':
                if Fin != Debut:
                    new_path.append(segment)
            else:
                new_path.append(segment)
        path = inkex.Path(new_path)

        # generate new elements from sub paths
        segments = iter(path)
        end = []
        try:
            segment = next(segments)
            start = segment
            segmentPrev = segment
            segment = next(segments)  # Sauter le premier M

            while segment.letter != 'Z':
                end = []
                # Si ce sont des arcs les garder dans un même chemin
                if segment.letter != 'A':
                    end.append(segment)
                    segmentPrev = segment
                    segment = next(segments)
                else:
                    while segment.letter == 'A':
                        end.append(segment)
                        segmentPrev = segment
                        segment = next(segments)
                if len(end) > 0:    # Si il y a des segments à ajouter les dessinner
                    start = start.end_point(None, None)
                    start = inkex.paths.Move(start.x, start.y)
                    segment_path = inkex.Path([start] + end)
                    new_element = inkex.PathElement(d=str(segment_path),
                                                    style=str(style),
                                                    transform=str(element.transform))
                    parent.insert(index, new_element)
                    inkex.utils.debug(f"Segment {segment_path}")  # **********************
                start = segmentPrev  # Le nouveau segment de départ est le dernier segment de la série précédente

        except StopIteration:
            inkex.utils.debug("=================== Stop itération ===================")  # **********************

        # remove the original element
        parent.remove(element)


if __name__ == '__main__':
    ToSubPaths().run()
