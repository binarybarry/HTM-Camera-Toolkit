The HTM Camera Toolkit is a research application that allows easy experimentation of Numenta's Hierarchical Temporal Memory (HTM) algorithms using real world video input from a camera/webcam.  

The Camera Toolkit runs a Python implementation of the HTM algorithm however I also have ANSI-C, C++, and Java implementations.  These are not currently hooked into the Camera Toolkit app.  I have been using them to experiment with other environments to compare performance (ANSI C, C++) and ease of access with other supporting tools (Swing+Hadoop in Java).  Both should be usable if you are interested in running the HTM algorithm code in your own research projects (note: the C++ version only has a partially implemented spatial pooler; ANSI C and Java should be complete).

The ANSI C version of HTM is my most recent work (as of Aug/Sept 2012).  As my experiments progressed it became clear that the ability to scale up to larger and longer data sets is very important.  Thus I needed a new implementation that was focused on optimizing for performance from the very start.  The ANSI C implementation has only minimal use of the
standard library as well as an optional dependence on OpenMP to enable parallel code.  This version does not include any UI front end for visualization.  Instead I have a suite of unit tests, performance tests, and examples.  If you are a researcher interested in HTM please take a look at this version if you can.  I will also be updating it the most going forward.


Also included in this project is my HMAX Camera Toolkit.  This is another research application that implements the HMAX computer vision algorithm.  This toolkit allows training multiple classes of objects using video input and later classifying subsequent video input frames as one of the several trained classes.

I haven't set up any formal installers as of yet.  So to run the toolkit you will need the following installed:

Python 2.6
wxPython 2.8
Python Imaging Library (PIL) 1.1.7
Numpy 1.5.1
OpenCV 2.1

You can download them from their websites, respectively:

http://www.python.org/download/
http://www.wxpython.org/download.php
http://www.pythonware.com/products/pil/
http://sourceforge.net/projects/numpy/files/NumPy/1.5.1/
http://opencv.willowgarage.com/wiki/


Building under Windows
======================

HTM Camera and HMAX Toolkits were tested under:
* Win7-64
* Vista-32
 
No special build instructions are needed under Windows since all the necessary libraries are part of the GIT tree.  Make sure your python installation is on the PYTHONPATH and python/OpenCV/libsvm.dll are all on the PATH.


Building under Linux
====================

HTM Camera and HMAX Toolkits were tested under:
* Linux Ubuntu 10.04

For HMAX you will need to install or build the LIBSVM 3rd party library available at http://www.csie.ntu.edu.tw/~cjlin/libsvm. Preferred version is 3.1.

The HMAX toolkit uses native c++ libraries for performance reasons.  Currently I only include pre-built libraries for win32.  You will need to recompile if desired to run on Linux.  To do this you will need gcc/mingw and SWIG installed (I use 2.0.4) and then run following commands to build _hmaxc.so:

cd src
python setup.py build
export PYTHONPATH=$PWD


Building under Mac
==================

HTM Camera Toolkit was tested under:
* Mac OSX 10.6 Snow Leopard
* Mac OSX 10.7 Lion

OpenCV and Python are very easy to install on Mac using MacPorts (www.macports.org).  MacPorts can download and install various Mac software projects with little effort.  Once you have MacPorts installed you can use it to obtain OpenCV and the Python tools using the following commands (thanks to crizCraig for recommending MacPorts):

sudo port install opencv +python26
sudo port install py26-pil
sudo port install py26-wxpython

The HMAX Toolkit requires recompiling the native c++ libraries.  Should work similar to Linux, but has not yet been tested on Mac.


Running under Windows/Linux/Mac
===============================

Once you have all of the above installed with proper PATH and PYTHONPATH environment variables set up, you can run the toolkit from a command-line:

cd src
python CameraToolkit.py
or
python HMAXToolkit.py

More detailed information is also posted on the Numenta HTM Theory forum:
http://www.numenta.com/phpBB2/viewtopic.php?t=1419

For HMAX, I am primarily referencing this paper:
Jim Mutch and David G. Lowe "Object class recognition and localization using sparse features with limited receptive fields" 2008.
Found at: http://www.cs.ubc.ca/~lowe/papers/08mutch.pdf


Additional background:

Numenta (www.numenta.com) is designing an exciting new technology based on models of the neocortex called "Hierarchical Temporal Memory".

Their most recent work on HTM, also called the "Cortical Learning Algorithms", is so far unreleased as a software project.  However they have published fairly detailed documentation as well as pseudo-code of how the overall algorithm works.

Numenta is currently allowing non-commerical experimentation by interested developers who wish to implement the ideas from the documention.  However, the algorithm is not free to use in any commericial or production setting.

With that said, the HTM Camera Toolkit includes my entire personal implementation of the HTM algorithms, as well as a full user-interface for aquiring video input from a camera (or video file) and feeding this data into an HTM Region (or up to 4 Regions set up in a hierarchy).

The toolkit also includes a full Region Visualization tool to very easily see the entire state of a Region at a given time step, including full Column and Cell states plus learning updates.  This is very useful when trying to follow how an HTM Region is performing given the inputs and the parameters over time.

I encourage anyone interested in Numenta and HTM to give my toolkit a try and see if it helps you understand how the Regions work with real world data.

If you are motivated enough, please also take a look at the code itself to review the details of my Region implementation. I gladly welcome any feedback or suggestions about how I am doing things or what I may be doing wrong.  An easy place for doing so is the 'HTM Theory' forum on www.numenta.com, I am 'binarybarry' there as well.



