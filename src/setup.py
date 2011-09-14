"""
Created on May 23, 2011

@author: barry

setup.py file for SWIG.

This file identifies C++ files that we wish to compile and
will run swig to create a python library containing the
compiled native code as well as a wrapper file so python
knows how to properly call into it.

On win32 you will need mingw32 installed and on the PATH.
To run (on win32) type the following on command line:

python setup.py build -c mingw32

Linux is the same but does not need the "-c mingw32".  
I assume it will default to using whichever gcc is on the 
PATH; most likely this will be fine.
"""

import os
import sys
import shutil
from distutils.core import setup, Extension

shutil.rmtree("build", ignore_errors=True)

cDir = "HMAX"+os.sep+"cpp"+os.sep
example_module = Extension('_hmaxc', [cDir+'LayerC.cpp',
                                      cDir+'GaborFilterC.cpp', 
                                      cDir+'MaxFilterC.cpp',
                                      cDir+'GRBFFilterC.cpp',
                                      cDir+'hmaxc.i'],
                           swig_opts=['-c++'])#, '-I../include'])

setup (name = 'hmaxc',
       version = '1.0',
       author      = "Barry",
       description = """HMAX C++ Library.""",
       ext_modules = [example_module]
       #py_modules = ["example"],
       )

shutil.copyfile(cDir+"hmaxc.py", "hmaxc.py")
if os.name == 'nt':
  shutil.copyfile("build"+os.sep+"lib.win32-2.6"+os.sep+"_hmaxc.pyd", "_hmaxc.pyd")
elif os.name == 'posix':
  shutil.copyfile("build"+os.sep+"lib.linux-i686-2.6"+os.sep+"_hmaxc.so", "_hmaxc.so")
else:
  sys.exit("do not know what to do under OS '" + os.name + "'")

#ext_modules=[Extension('_foo', ['foo.i'],
#                             swig_opts=['-modern', '-I../include'])]
