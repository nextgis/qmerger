# -*- coding: utf-8 -*-
"""
/***************************************************************************
 qmerger
                                 A QGIS plugin
 Merge vector layers
                             -------------------
        begin                : 2015-03-26
        copyright            : (C) 2015 by NextGIS
        email                : info@nextgis.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load qmerger class from file qmerger.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .qmerger import qmerger
    return qmerger(iface)
