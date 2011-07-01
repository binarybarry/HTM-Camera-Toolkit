'''
Created on May 23, 2011

@author: barry
'''

"""
setup.py file for SWIG example
"""

import os
import shutil
from distutils.core import setup, Extension

shutil.rmtree("build", ignore_errors=True)

cDir = ".."+os.sep+".."+os.sep+"hmin"+os.sep+"CLA"+os.sep
example_module = Extension('_hmaxc', [cDir+'LayerC.cpp',
                                      cDir+'GaborFilterC.cpp', 
                                      cDir+'MaxFilterC.cpp',
                                      cDir+'hmaxc.i'],
                           swig_opts=['-c++'])#, '-I../include'])

setup (name = 'hmaxc',
       version = '0.1',
       author      = "Barry",
       description = """HMAX C++ Library.""",
       ext_modules = [example_module]
       #py_modules = ["example"],
       )

shutil.copyfile(cDir+"hmaxc.py", "hmaxc.py")
shutil.copyfile("build"+os.sep+"lib.win32-2.6"+os.sep+"_hmaxc.pyd", "_hmaxc.pyd")

#ext_modules=[Extension('_foo', ['foo.i'],
#                             swig_opts=['-modern', '-I../include'])]