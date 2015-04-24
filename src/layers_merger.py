# -*- coding: utf-8 -*-

#******************************************************************************
#
# MergeShapes
# ---------------------------------------------------------
# Create points from coordinates
#
# Copyright (C) 2010-2013 Alexander Bruy (alexander.bruy@gmail.com)
#
# This source is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# This code is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# A copy of the GNU General Public License is available on the World Wide Web
# at <http://www.gnu.org/copyleft/gpl.html>. You can also obtain it by writing
# to the Free Software Foundation, Inc., 59 Temple Place - Suite 330, Boston,
# MA 02111-1307, USA.
#
#******************************************************************************

from PyQt4.QtCore import *
from qgis.core import *

from vector_writer import VectorWriter


class LayerMergeThread(QThread):
    rangeChanged = pyqtSignal(int)
    checkStarted = pyqtSignal()
    featureProcessed = pyqtSignal()
    checkFinished = pyqtSignal()
    fileNameChanged = pyqtSignal(str)
    shapeProcessed = pyqtSignal()
    processingFinished = pyqtSignal()
    processingInterrupted = pyqtSignal()

    def __init__(self, input_layers, outputFileName, outputEncoding, outputCrs, outputGeomType, addFileName, addFilePath):
        QThread.__init__(self, QThread.currentThread())
        self.input_layers = input_layers
        # output
        self.outputFileName = outputFileName
        self.outputEncoding = outputEncoding
        self.outputCrs = outputCrs
        self.outputGeomType = outputGeomType
        # params
        self.addFileName = addFileName
        self.addFilePath = addFilePath

        self.mutex = QMutex()
        self.stopMe = 0

    def run2(self):
        self.mutex.lock()
        self.stopMe = 0
        self.mutex.unlock()

        interrupted = False

        # create attribute list with uniquie fields
        # from all selected layers
        merged_fields = QgsFields()
        self.rangeChanged.emit(len(self.input_layers))
        self.checkStarted.emit()
        for layer in self.input_layers:
            dp = layer.dataProvider()
            layer_fields = dp.fields()
            for layer_field in layer_fields:
                field_found = False
                for merged_field in merged_fields:
                    if (merged_field.name() == layer_field.name()) and (merged_field.type() == layer_field.type()):
                        field_found = True
                if not field_found:
                    merged_fields.append(layer_field)
            self.featureProcessed.emit()
        self.checkFinished.emit()

        # add extra fields
        if self.addFileName:
            f = QgsField("file_name", QVariant.String, "", 255)
            self.fNameIndex = len(self.fields) + 1
            self.fields.append(f)
            merged_fields.append(f)

        if self.addFilePath:
            f = QgsField("file_path", QVariant.String, "", 255)
            self.fields.append(f)
            merged_fields.append(f)

        self.fields = merged_fields


        # create writer
        writer = VectorWriter(self.outputFileName,
                                     self.outputEncoding,
                                     self.fields,
                                     self.outputGeomType,
                                     self.outputCrs)

        for layer in self.input_layers:

            dp = layer.dataProvider()
            layer_fields = dp.fields()

            n_feat = dp.featureCount()

            self.rangeChanged.emit(n_feat)
            self.fileNameChanged.emit(layer.name())  #??? filename

            out_feat = QgsFeature()
            for f in layer.getFeatures():
                out_feat.setFields(self.fields, True)
                # fill available attributes with values
                for layer_field in layer_fields:
                    for merged_field in self.fields:
                        if (merged_field.name() == layer_field.name()) and (merged_field.type() == layer_field.type()):
                            out_feat[merged_field.name()] = f[merged_field.name()]
                in_geom = QgsGeometry(f.geometry())
                out_feat.setGeometry(in_geom)

                if self.addFileName:
                    out_feat.setAttribute('file_name', layer.name())  #??? fileName
                if self.addFilePath:
                    out_feat.setAttribute('file_path',  layer.name())  #??? QDir().toNativeSeparators(self.baseDir + "/" + fileName))

                writer.addFeature(out_feat)
                self.featureProcessed.emit()

            self.shapeProcessed.emit()
            self.mutex.lock()
            s = self.stopMe
            self.mutex.unlock()
            if s == 1:
                interrupted = True
                break

        self.memLayer = writer.memLayer
        self.fileName = writer.fileName

        del writer

        if not interrupted:
            self.processingFinished.emit()
        else:
            self.processingInterrupted.emit()

    def stop(self):
        self.mutex.lock()
        self.stopMe = 1
        self.mutex.unlock()

        QThread.wait(self)
