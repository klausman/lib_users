#!/usr/bin/env python

from distutils.core import setup

setup(name='lib_users',
      version='0.12',
      description='Checks /proc for libraries and files being mapped/open '
		  'but marked as deleted',
      author='Tobias Klausmann',
      author_email='klausman@schwarzvogel.de',
      url='https://github.com/klausman/lib_users',
      packages=['lib_users_util'],
      scripts=['lib_users.py', 'fd_users.py'],
     )
