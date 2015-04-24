# -*- coding: utf-8 -*-
"""
/***************************************************************************
 qmergerDialog
                                 A QGIS plugin
 Merge vector layers
                             -------------------
        begin                : 2015-03-26
        git sha              : $Format:%H$
        copyright            : (C) 2015 by NextGIS
        email                : info@nextgis.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from PyQt4 import QtGui, uic
from PyQt4.QtCore import QSettings, Qt
from PyQt4.QtGui import QTableWidget, QStandardItemModel, QStandardItem, QHeaderView, QColor, QAbstractItemView, \
    QMessageBox, QDialogButtonBox, QCheckBox
from qgis.core import QGis, QgsCoordinateReferenceSystem, QgsVectorDataProvider, QgsMapLayer, QgsMapLayerRegistry
from qgis.gui import QgsMessageBar
from layers_merger import LayerMergeThread

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qmerger_dialog_base.ui'))

# TODO: refactor this! Need set Default crs
DEFAULT_OUT_CRS = QgsCoordinateReferenceSystem()
DEFAULT_OUT_CRS.createFromSrid(4326)

SOURCE_TYPE_LAYERS = 'layers'
SOURCE_TYPE_DIR = 'dir'
SOURCE_TYPE_FILES = 'files'



class qmergerDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, iface, parent=None):
        """Constructor."""
        super(qmergerDialog, self).__init__(parent)
        self.setupUi(self)

        # Vars
        self.iface = iface
        self.mem_layers = []
        self.input_layers = []

        self.geom_types = {
            QGis.WKBPoint:              self.tr('Point'),
            QGis.WKBLineString:         self.tr('Line'),
            QGis.WKBPolygon:            self.tr('Polygon'),
            QGis.WKBMultiPoint:         self.tr('MultiPoint'),
            QGis.WKBMultiLineString:    self.tr('MultiLine'),
            QGis.WKBMultiPolygon:       self.tr('MultiPolygon'),
            QGis.WKBPoint25D:           self.tr('Point 2.5D'),
            QGis.WKBLineString25D:      self.tr('LineString 2.5D'),
            QGis.WKBPolygon25D:         self.tr('Polygon 2.5D'),
            QGis.WKBMultiPoint25D:      self.tr('MultiPoint 2.5D'),
            QGis.WKBMultiLineString25D: self.tr('MultiLineString 2.5D'),
            QGis.WKBMultiPolygon25D:    self.tr('MultiPolygon 2.5D')
        }

        # ResultGeomType: (Alias, OtherSuitableTypes)
        self.result_geom_types = {
            QGis.WKBPoint:              (self.tr('Point'), [QGis.WKBPoint25D]),
            QGis.WKBLineString:         (self.tr('Line'), [QGis.WKBLineString25D]),
            QGis.WKBPolygon:            (self.tr('Polygon'), [QGis.WKBPolygon25D]),
            QGis.WKBMultiPoint:         (self.tr('MultiPoint'), [QGis.WKBMultiPoint25D, QGis.WKBPoint]),
            QGis.WKBMultiLineString:    (self.tr('MultiLine'), [QGis.WKBMultiLineString25D, QGis.WKBLineString]),
            QGis.WKBMultiPolygon:       (self.tr('MultiPolygon'), [QGis.WKBMultiPolygon25D, QGis.WKBPolygon]),
        }

        # GUI
        self._init_gui()
        self.on_source_type_changed(0)

        # Signals
        self.cmbSourceType.currentIndexChanged.connect(self.on_source_type_changed)
        self.cmbGeometryType.currentIndexChanged.connect(self.fill_input_layers_tbl)
        self.buttonBox.button(QDialogButtonBox.Apply).clicked.connect(self.start_merge_layers)

        #import pydevd
        #pydevd.settrace('localhost', port=9921, stdoutToServer=True, stderrToServer=True, suspend=False)


    def _init_gui(self):
        # Fill geometry type cmb
        def _sort_geom_types(a, b):
            if a[0] < 0 and b[0] < 0:
                return a[0] - b[0]
            if a[0] < 0:
                return +1
            if b[0] < 0:
                return -1
            return a[0] - b[0]

        self.cmbGeometryType.clear()
        for (key, val) in sorted(self.result_geom_types.iteritems(), cmp=_sort_geom_types):
            self.cmbGeometryType.addItem(val[0], key)

        # Fill source type cmb
        self.cmbSourceType.clear()
        self.cmbSourceType.addItem(self.tr('Selected layers in TOC'), SOURCE_TYPE_LAYERS)
        self.cmbSourceType.addItem(self.tr('From directory'), SOURCE_TYPE_DIR)
        self.cmbSourceType.addItem(self.tr('Selected files'), SOURCE_TYPE_FILES)

        # Fill encoding cmb
        self.cmbOutEncoding.clear()
        self.cmbOutEncoding.addItems(QgsVectorDataProvider.availableEncodings())
        enc = QSettings().value("/UI/encoding", "System")
        enc_index = self.cmbOutEncoding.findText(enc)
        if enc_index < 0:
            self.cmbOutEncoding.insertItem(0, enc)
            enc_index = 0
        self.cmbOutEncoding.setCurrentIndex(enc_index)

        # Fill Crs cmb
        self.cmbOutSpatialReference.setCrs(DEFAULT_OUT_CRS)

        # Init layers table
        self.input_layers_model = QStandardItemModel(self.tblInputLayers)
        self.tblInputLayers.setModel(self.input_layers_model)
        #self.tblInputLayers.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)
        self.tblInputLayers.horizontalHeader().setResizeMode(QHeaderView.Stretch)
        self.tblInputLayers.verticalHeader().hide()
        self.tblInputLayers.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tblInputLayers.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.clear_table()


    @property
    def selected_source_type(self):
        return self.cmbSourceType.itemData(self.cmbSourceType.currentIndex())

    @property
    def selected_geometry_type(self):
        return self.cmbGeometryType.itemData(self.cmbGeometryType.currentIndex())

    def clear_table(self):
        self.input_layers_model.clear()
        self.input_layers_model.setColumnCount(3)
        headers = (
            self.tr('Layer'),
            self.tr('Type'),
            self.tr('CRS')
            #self.tr('Provider')
        )
        self.input_layers_model.setHorizontalHeaderLabels(headers)


    def on_source_type_changed(self, ind):
        source_type = self.selected_source_type
        # set active input layers
        if source_type == SOURCE_TYPE_LAYERS:
            self.input_layers = self.get_layers_from_toc()
        if source_type == SOURCE_TYPE_DIR:
            self.input_layers = self.get_layers_from_dir()
        if source_type == SOURCE_TYPE_FILES:
            self.input_layers = self.get_layers_from_files()
        # set gui
        self.pnlDir.setVisible(source_type == SOURCE_TYPE_DIR)
        self.pnlFiles.setVisible(source_type == SOURCE_TYPE_FILES)

        self.fill_input_layers_tbl()

        # temporary
        if source_type in [SOURCE_TYPE_DIR, SOURCE_TYPE_FILES]:
            self.pnlDir.setDisabled(True)
            self.pnlFiles.setDisabled(True)
            self.tblInputLayers.setDisabled(True)
        else:
            self.tblInputLayers.setDisabled(False)

    def fill_input_layers_tbl(self):
        self.clear_table()
        for layer in self.input_layers:
            is_error = False
            is_warning = False
            # Layer
            item_layer = QStandardItem(layer.name())
            item_layer.setData(layer.dataUrl(), Qt.ToolTipRole)
            # Type
            if not layer.isValid():
                text = 'Unsupported layer'
                item_type = QStandardItem(text)
                is_error = True
            elif layer.type() in [QgsMapLayer.RasterLayer, QgsMapLayer.PluginLayer]:
                text = 'Unsupported layer'
                item_type = QStandardItem(text)
                is_error = True
            else:
                layer_geom_type = layer.wkbType()
                if layer_geom_type in self.geom_types.keys():
                    text = self.geom_types[layer_geom_type]
                else:
                    text = 'Unsupported geometry type'
                    is_error = True

                item_type = QStandardItem(text)

                if layer_geom_type != self.selected_geometry_type:
                    if layer_geom_type in self.result_geom_types[self.selected_geometry_type][1]:
                        is_warning = True
                    else:
                        is_error = True

            # CRS
            item_crs = QStandardItem(layer.crs().authid())

            if is_error:
                error_color = QColor.fromRgb(255, 156, 176)
                item_layer.setData(error_color, Qt.BackgroundColorRole)
                item_type.setData(error_color, Qt.BackgroundColorRole)
                item_crs.setData(error_color, Qt.BackgroundColorRole)
            if is_warning:
                warning_color = QColor.fromRgb(230, 220, 128)
                item_layer.setData(warning_color, Qt.BackgroundColorRole)
                item_type.setData(warning_color, Qt.BackgroundColorRole)
                item_crs.setData(warning_color, Qt.BackgroundColorRole)

            self.input_layers_model.appendRow([item_layer, item_type, item_crs])

        #strech table columns
        #self.tblInputLayers.resizeColumnsToContents()

    def get_layers_from_toc(self):
        return self.iface.legendInterface().selectedLayers()

    def get_layers_from_dir(self):
        return []

    def get_layers_from_files(self):
        return []

    def start_merge_layers(self):
        # Filter layers
        suitable_layers = []
        for layer in self.input_layers:
            if layer.isValid() and \
               layer.type() == QgsMapLayer.VectorLayer and \
               (layer.wkbType() == self.selected_geometry_type or
                layer.wkbType() in self.result_geom_types[self.selected_geometry_type][1]):
                    suitable_layers.append(layer)

        #TODO: check!
        if len(suitable_layers) < 2:
            QMessageBox.warning(self,
                                self.tr('QMerger'),
                                self.tr('Requires at least two suitable layer!'))
            return

        self.layer_merger = LayerMergeThread(suitable_layers,
                                             'memory:',
                                             self.cmbOutEncoding,
                                             self.cmbOutSpatialReference.crs(),
                                             self.selected_geometry_type,
                                             self.chkAddFileName.isChecked(),
                                             self.chkAddFilePath.isChecked())

        self.layer_merger.processingFinished.connect(self.processingFinished)
        self.layer_merger.processingInterrupted.connect(self.processingInterrupted)

        self.layer_merger.run2()

    def processingFinished(self):
        if self.chkAddResultToMap.isChecked():
            self.mem_layers.append(self.layer_merger.memLayer)
            QgsMapLayerRegistry.instance().addMapLayer(self.layer_merger.memLayer)

        self.stopProcessing()

        self.iface.messageBar().pushMessage(self.tr("QMerge"),
                                            self.tr("Result layer was added to the map"),
                                            level=QgsMessageBar.INFO,
                                            duration=5)
        self.close()

    def processingInterrupted(self):
        #self.restoreGui()
        pass

    def stopProcessing(self):
        if self.layer_merger:
            self.layer_merger.stop()
            self.layer_merger = None
