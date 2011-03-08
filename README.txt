The HTM Camera Toolkit is a research application that allows easy experimentation of Numenta's Hierarchical Temporal Memory (HTM) algorithms using real world video input from a camera/webcam.

I haven't set up any formal installers as of yet.  So to run the toolkit you will need the following installed:

Python 2.7
wxPython 2.8
Python Imaging Library (PIL) 1.1.7
Numpy 1.5.1
OpenCV 2.2

You get download them from their websites, respectively:

http://www.python.org/download/
http://www.wxpython.org/download.php
http://www.pythonware.com/products/pil/
http://sourceforge.net/projects/numpy/files/NumPy/1.5.1/
http://opencv.willowgarage.com/wiki/

Once you have all of the above, you can run the toolkit from a command-line:

python CameraToolkit.py



Additional background:

Numenta (www.numenta.com) is designing an exciting new technology based on models of the neocortex called "Hierarchical Temporal Memory".

Their most recent work on HTM, also called the "Cortical Learning Algorithms", is so far unreleased as a software project.  However they have published fairly detailed documentation as well as pseudo-code of how the overall algorithm works.

Numenta is currently allowing non-commerical experimentation by interested developers who wish to implement the ideas from the documention.  However, the algorithm is not free to use in any commericial or production setting.

With that said, the HTM Camera Toolkit includes my entire personal implementation of the HTM algorithms, as well as a full user-interface for aquiring video input from a camera (or video file) and feeding this data into an HTM Region (or up to 4 Regions set up in a hierarchy).

The toolkit also includes a full Region Visualization tool to very easily see the entire state of a Region at a given time step, including full Column and Cell states plus learning updates.  This is very useful when trying to follow how an HTM Region is performing given the inputs and the parameters over time.

I encourage anyone interested in Numenta and HTM to give my toolkit a try and see if it helps you understand how the Regions work with real world data.

If you are motivated enough, please also take a look at the code itself to review the details of my Region implementation. I gladly welcome any feedback or suggestions about how I am doing things or what I may be doing wrong.  An easy place for doing so is the 'HTM Theory' forum on www.numenta.com, I am 'binarybarry' there as well.



