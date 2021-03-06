# This file is part of Indico.
# Copyright (C) 2002 - 2016 European Organization for Nuclear Research (CERN).
#
# Indico is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# Indico is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Indico; if not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from MaKaC.webinterface.pages.base import WPJinjaMixin
from MaKaC.webinterface.pages.category import WPCategoryDisplayBase
from MaKaC.webinterface.wcomponents import WSimpleNavigationDrawer


class WPCategoryStatistics(WPJinjaMixin, WPCategoryDisplayBase):
    template_prefix = 'categories/'

    def _getBody(self, params):
        return self._getPageContent(params)

    def _getNavigationDrawer(self):
        return WSimpleNavigationDrawer(self._target.getName(), type='Statistics')

    def getJSFiles(self):
        return (WPCategoryDisplayBase.getJSFiles(self) + self._includeJSPackage('jqplot_js', prefix='')
                + self._asset_env['statistics_js'].urls() + self._asset_env['modules_category_statistics_js'].urls())

    def getCSSFiles(self):
        return WPCategoryDisplayBase.getCSSFiles(self) + self._asset_env['jqplot_css'].urls()
