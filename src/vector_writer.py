# -*- coding: utf-8 -*-

"""
***************************************************************************
    vector.py
    ---------------------
    Date                 : February 2013
    Copyright            : (C) 2013 by Victor Olaya
    Email                : volayaf at gmail dot com
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

__author__ = 'Victor Olaya'
__date__ = 'February 2013'
__copyright__ = '(C) 2013, Victor Olaya'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import uuid

from PyQt4.QtCore import QVariant, QSettings
from qgis.core import QGis, QgsFields, QgsField, QgsVectorLayer, QgsVectorFileWriter


GEOM_TYPE_MAP = {
    QGis.WKBPoint:              'Point',
    QGis.WKBLineString:         'LineString',
    QGis.WKBPolygon:            'Polygon',
    QGis.WKBMultiPoint:         'MultiPoint',
    QGis.WKBMultiLineString:    'MultiLineString',
    QGis.WKBMultiPolygon:       'MultiPolygon',
    QGis.WKBPoint25D:           'Point',     #hack
    QGis.WKBLineString25D:      'LineString',
    QGis.WKBPolygon25D:         'Polygon',
    QGis.WKBMultiPoint25D:      'MultiPoint',
    QGis.WKBMultiLineString25D: 'MultiLineString',
    QGis.WKBMultiPolygon25D:    'WKBMultiPolygon'
}

TYPE_MAP = {
    str: QVariant.String,
    float: QVariant.Double,
    int: QVariant.Int,
    bool: QVariant.Bool
}


class VectorWriter:

    MEMORY_LAYER_PREFIX = 'memory:'

    def __init__(self, fileName, encoding, fields, geometryType, crs, options=None):
        self.fileName = fileName
        self.isMemory = False
        self.memLayer = None
        self.writer = None

        if encoding is None:
            settings = QSettings()
            encoding = settings.value('/Processing/encoding', 'System', type=str)

        if self.fileName.startswith(self.MEMORY_LAYER_PREFIX):
            self.isMemory = True

            uri = GEOM_TYPE_MAP[geometryType] + "?uuid=" + str(uuid.uuid4())
            if crs.isValid():
                uri += '&crs=' + crs.authid()

            fieldsdesc = ['field=' + self._fieldName(f) for f in fields]
            if fieldsdesc:
              uri += '&' + '&'.join(fieldsdesc)

            self.memLayer = QgsVectorLayer(uri, self.fileName, 'memory')
            self.writer = self.memLayer.dataProvider()
        else:
            formats = QgsVectorFileWriter.supportedFiltersAndFormats()
            OGRCodes = {}
            for (key, value) in formats.items():
                extension = unicode(key)
                extension = extension[extension.find('*.') + 2:]
                extension = extension[:extension.find(' ')]
                OGRCodes[extension] = value

            extension = self.fileName[self.fileName.rfind('.') + 1:]
            if extension not in OGRCodes:
                extension = 'shp'
                self.fileName = self.fileName + '.shp'

            qgsfields = QgsFields()
            for field in fields:
                qgsfields.append(self._toQgsField(field))

            self.writer = QgsVectorFileWriter(
                self.fileName, encoding,
                qgsfields, geometryType, crs, OGRCodes[extension])

    def addFeature(self, feature):
        if self.isMemory:
            self.writer.addFeatures([feature])
        else:
            self.writer.addFeature(feature)

    def _fieldName(self, f):
        if isinstance(f, basestring):
            return f
        return f.name()


    def _toQgsField(self, f):
        if isinstance(f, QgsField):
            return f
        return QgsField(f[0], TYPE_MAP.get(f[1], QVariant.String))
