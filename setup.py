# -*- coding: utf-8 -*-
##
## $Id: setup.py,v 1.122 2009/06/17 15:27:43 jose Exp $
##
## This file is part of CDS Indico.
## Copyright (C) 2002, 2003, 2004, 2005, 2006, 2007 CERN.
##
## CDS Indico is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of the
## License, or (at your option) any later version.
##
## CDS Indico is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with CDS Indico; if not, write to the Free Software Foundation, Inc.,
## 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

# Autoinstalls setuptools if the user doesn't have them already
import ez_setup
ez_setup.use_setuptools()

import commands
import getopt
import os
import re
import shutil
import string
import sys
from distutils.sysconfig import get_python_lib
from distutils.cmd import Command

import pkg_resources
from setuptools.command import develop, install, sdist, bdist_egg, easy_install
from setuptools import setup, find_packages, findall
from subprocess import Popen, PIPE

if sys.platform == 'linux2':
    import pwd
    import grp

import tests

class vars(object):
    '''Variable holder.'''
    packageDir = None
    versionVal = 'None'
    accessuser = None
    accessgroup = None
    dbInstalledBySetupPy = False
    binDir = None
    documentationDir = None
    configurationDir = None
    htdocsDir = None

###  Methods required by setup() ##############################################

def _getDataFiles(x):
    """
    Returns a fully populated data_files ready to be fed to setup()

    WARNING: when creating a bdist_egg we need to include files inside bin,
    doc, config & htdocs into the egg therefore we cannot fetch indico.conf
    values directly because they will not refer to the proper place. We
    include those files in the egg's root folder.
    """
    dataFilesDict = {}

    # setup expects a list like this (('foo/bar/baz', 'wiki.py'),
    #                                 ('a/b/c', 'd.jpg'))
    #
    # What we do below is transform a list like this:
    #                                (('foo', 'bar/baz/wiki.py'),
    #                                 ('a', 'b/c/d.jpg'))
    #
    # first into a dict and then into a pallatable form for setuptools.

    # This re will be used to filter out etc/*.conf files and therefore not overwritting them
    isAConfRe = re.compile('etc\/[^/]+\.conf$')

    for (baseDstDir, files, remove_first_x_chars) in (('bin',           findall('bin'), 4),
                                                      ('doc', ['doc/UserGuide.pdf','doc/AdminUserGuide.pdf'], 4),
                                                      ('etc', [xx for xx in findall('etc') if not isAConfRe.search(xx)], 4),
#                                                      ('MaKaC',              findall('indico/MaKaC'), 13),
                                                      ('htdocs',        findall('indico/htdocs'), 14),
                                                      ):
        for f in files:
            dst_dir = os.path.join(baseDstDir, os.path.dirname(f)[remove_first_x_chars:])
            if dst_dir not in dataFilesDict:
                dataFilesDict[dst_dir] = []
            dataFilesDict[dst_dir].append(f)

    dataFiles = []
    for k, v in dataFilesDict.items():
        dataFiles.append((k, v))

    return dataFiles





def _getInstallRequires():
    '''Returns external packages required by Indico

    They will only be installed when Indico is installed through easy_install.'''

    base =  ['pytz', 'zodb3', 'jstools', 'zope.index', 'zope.interface', 'simplejson']
    if sys.version_info[1] < 5: # hashlib is part of Python 2.5+
        base.append('hashlib')

    return base


def _versionInit():
        '''Writes a version number inside indico/MaKaC/__init__.py and returns it'''
        global x
        v = None
        for k in sys.argv:
            if k == '--version':
                v = sys.argv[sys.argv.index(k) + 1]
                break

        if not v:
            v = raw_input('Version being packaged [dev]: ').strip()
            if v == '':
                v = 'dev'

        old_init = open('indico/MaKaC/__init__.py','r').read()
        new_init = re.sub('(__version__[ ]*=[ ]*[\'"]{1})([^\'"]+)([\'"]{1})', "\\g<1>%s\\3" % v, old_init)
        open('indico/MaKaC/__init__.py', 'w').write(new_init)
        return v



def _convertdoc():
    '''Generates INSTALL from INSTALL.xml'''
    commands.getoutput('docbook2html --nochunks doc/docbook_src/INSTALL.xml > INSTALL.html')
    commands.getoutput('docbook2pdf doc/docbook_src/INSTALL.xml')
    commands.getoutput('w3m INSTALL.html > INSTALL')
    commands.getoutput('rm INSTALL.html')


###  Commands ###########################################################
class sdist_indico(sdist.sdist):
    user_options = sdist.sdist.user_options + \
                   [('version=', None, 'version to distribute')]
    version = 'dev'

    def run(self):
        global x
        _convertdoc()
        jsCompress()
        sdist.sdist.run(self)

class bdist_egg_indico(bdist_egg.bdist_egg):
    def run(self):
        _convertdoc()
        bdist_egg.bdist_egg.run(self)


class jsbuild(Command):
    description = "minifies and packs javascript files"
    user_options = []
    boolean_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        from MaKaC.consoleScripts.installBase import jsCompress
        jsCompress()

class fetchdeps_indico(Command):
    description = "fetch all the dependencies needed to run Indico"
    user_options = []
    boolean_options = []

    def initialize_options(self): pass

    def finalize_options(self): pass

    def run(self):
        print "Checking if dependencies need to be installed..."

        wset = pkg_resources.working_set

        wset.resolve(map(pkg_resources.Requirement.parse, _getInstallRequires()),
                           installer = self._installMissing)

        print "Done!"


    def _installMissing(self, dist):
        env = pkg_resources.Environment()
        easy_install.main(["-U",str(dist)])
        env.scan()
        return env[str(dist)][0]

class develop_indico(Command):
    description = "prepares the current directory for Indico development"
    user_options = []
    boolean_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):

        local = 'etc/indico.conf'
        if os.path.exists(local):
            print 'Upgrading existing etc/indico.conf..'
            upgrade_indico_conf(local, 'etc/indico.conf.sample')
        else:
            print 'Creating new etc/indico.conf..'
            shutil.copy('etc/indico.conf.sample', local)

        for f in [x for x in ('etc/zdctl.conf', 'etc/zodb.conf') if not os.path.exists(x)]:
            shutil.copy('%s.sample' % f, f)

        print """\nIndico needs to store some information in the filesystem (database, cache, temporary files, logs...)
Please specify the directory where you'd like it to be placed.
(Note that putting it outside of your sourcecode tree is recommended)"""
        prefixDir = raw_input('[%s]: ' % os.getcwd()).strip()

        if prefixDir == '':
            prefixDir = os.getcwd()

        directories = dict((d,os.path.join(prefixDir, d)) for d in
                           ['db', 'log', 'tmp', 'cache'])

        print 'Creating directories...',
        for d in directories.values():
            if not os.path.exists(d):
                os.makedirs(d)
        print 'Done!'

        directories['htdocs'] = os.path.join(os.getcwd(), 'indico', 'htdocs')

        from MaKaC.consoleScripts.installBase import _databaseText, _findApacheUserGroup, _checkDirPermissions

        if sys.platform == "linux2":
            # find the apache user/group
            user, group = _findApacheUserGroup(None, None)
            _checkDirPermissions(directories, accessuser=user, accessgroup=group)

        updateIndicoConfPathInsideMaKaCConfig(os.path.join(os.path.dirname(__file__), ''), 'indico/MaKaC/common/MaKaCConfig.py')
        compileAllLanguages()
        print '''
%s
        ''' % _databaseText('etc')

class tests_indico(Command):
    description = "run the test suite"
    user_options = []
    boolean_options = []

    def initialize_options(self): pass

    def finalize_options(self): pass

    def run(self):
        p = Popen("%s tests/__init__.py" % sys.executable, shell=True, stdout=PIPE, stderr=PIPE)
        out = string.join(p.stdout.readlines() )
        outerr = string.join(p.stderr.readlines() )
        print out, outerr


if __name__ == '__main__':
    sys.path = ['indico'] + sys.path # Always load source from the current folder

    #PWD_INDICO_CONF = 'etc/indico.conf'
    #if not os.path.exists(PWD_INDICO_CONF):
    #    shutil.copy('etc/indico.conf.sample', PWD_INDICO_CONF)

    from MaKaC.consoleScripts.installBase import *
    setIndicoInstallMode(True)

    if 'bdist_egg' in sys.argv:
        jsCompress()

    x = vars()
    x.packageDir = os.path.join(get_python_lib(), 'MaKaC')

    if ('--single-version-externally-managed' not in sys.argv) and \
    ('build' not in sys.argv):
        x.versionVal = _versionInit()

    x.binDir = 'bin'
    x.documentationDir = 'doc'
    x.configurationDir = 'etc'
    x.htdocsDir = 'htdocs'

    setup(name = "cds-indico",
          cmdclass={'sdist': sdist_indico,
                    'bdist_egg': bdist_egg_indico,
                    'jsbuild': jsbuild,
                    'tests': tests_indico,
                    'fetchdeps': fetchdeps_indico,
                    'develop': develop_indico,
                    },

          version = x.versionVal,
          description = "Integrated Digital Conference",
          author = "Indico Team",
          author_email = "indico-project@cern.ch",
          url = "http://cern.ch/indico",
          download_url = "http://cern.ch/indico/download-beta.html",
          platforms = ["any"],
          long_description = "Integrated Digital Conference",
          license = "http://www.gnu.org/licenses/gpl-2.0.txt",
          package_dir = { '': 'indico' },
          entry_points = {
            'console_scripts': [ 'taskDaemon           = MaKaC.consoleScripts.taskDaemon:main',
                                 'indico_initial_setup = MaKaC.consoleScripts.indicoInitialSetup:main',
                                 'indico_ctl           = MaKaC.consoleScripts.indicoCtl:main',
                                 ]
          },
          zip_safe = False,
          packages = find_packages(where='indico', exclude=('htdocs',)),
          install_requires = _getInstallRequires(),
          data_files = _getDataFiles(x),
          package_data = {'indico': ['*.*'] },
          include_package_data = True,
          )
