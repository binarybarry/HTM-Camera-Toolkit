"""
Created on May 18, 2011

@author: Barry Maturkanich

This file contains the definition of a single hierarchical level
within an HMAX network.

In an HMAX Network a Level is defined as a set of Layers 
(one per scale) as well as a single LevelFilter that defines rules
for processing input from previous level layers to produce the
data in the layers of the current level.
"""

import numpy
import Util
import HMAX
from PIL import Image

class Level(object):
  """
  In an HMAX Network a Level is defined as a set of Layers 
  (one per scale) as well as a single LevelFilter that defines rules
  for processing input from previous level layers to produce the
  data in the layers of the current level.
  """
  
  def __init__(self, network, name, index, filter):
    """
    @param network: the parent HMAX network this level belongs to.
    @param name: a name string to use when labeling UI or printing info.
    @param index: the level index indicating vertical position in hierarchy.
    @param filter: an object derived from LevelFilter that determines
    how layers in this level are to be calculated from layers in the
    previous level.
    """
    self.name = name
    self.filter = filter
    self.layers = None
    self.__network = network
    self.__index = index
  
  @property
  def network(self):
    return self.__network
  
  @property
  def index(self):
    return self.__index
  
  def __repr__(self):
    return self.name+" ("+str(self.index)+")"
  
  def setLayers(self, layers):
    """
    Assign the data layers used within this level.
    @param layers: the set of scale layers that will define this level.
    """
    self.layers = layers
    if HMAX.DEBUG:#Debug
      print "\n"+self.name
      for layer in self.layers:
        print layer
  
  def getMaxLayerValue(self):
    """ 
    Loop over all cells within all layers in this level and return
    the maximum value found.  This value is helpful when rendering
    layer data into an image as in this case we best want to know
    how to map the range of layer values into the 0-255 pixel range.
    """
    mx = 0.0
    for layer in self.layers:
      for f in xrange(layer.fSize):
        mx = max(mx, numpy.max(layer.getLayerData(f)))
    if mx==0.0:
      mx = 1.0
    return mx
  
  def computeLevel(self):
    """ 
    Use the filter defined for this level to compute the results for
    all the layers associated with this level. The filter will compute
    a value for each location in each layer.  For input(s) to a given
    layer, the filter will refer to the layerInputs that are defined
    for each layer.  The layerInputs are assumed to already have been
    computed by the previous level in the hierarchy.
    """
    for layer in self.layers:
      self.filter.computeLayer(layer)
  

class ImageLevel(Level):
  """ 
  An ImageLevel is a subclassed level that behaves slightly different
  in its computeLevel method.  In the case of images (level 0) we need to
  read from a raw image input source which does not map to any other
  input layers (of course not because it is the bottom-most layer).
  """
  
  def __init__(self, network, name, index, filter):
    Level.__init__(self, network, name, index, filter)
    
  def computeLevel(self, inputImage):
    """
    Compute the results for all layers associated with this level.
    In the case of the ImageLevel we must read our inputs from an
    outside source (the image specified by the inputImage parameter).
    In this case our level simply converts the PIL input image into
    a numpy array stored in the layers.  The first layer contains
    the exact image (100% scale) which subsequent layers store
    scaled-down versions of the input image.
    """
    assert inputImage.size==(self.layers[0].xSize, self.layers[0].ySize)
    self.layers[0].setLayerData(Util.convertPILtoNumpy(inputImage, False))
    
    #print "inferring "+self.name+"..."
    for layer in self.layers[1:]:
      ri = inputImage.resize((layer.xSize,layer.ySize), Image.BILINEAR)
      layer.setLayerData(Util.convertPILtoNumpy(ri, False))
  
  