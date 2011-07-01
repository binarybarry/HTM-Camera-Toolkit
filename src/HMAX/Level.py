"""
Created on May 18, 2011

@author: barry
"""

import numpy
import Util
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
    @param layers: the set of scale layers that will define this level.
    @param inputLayerIDs: numpy array of previous layer relative indicies to use
    as input to the layers in this level.  The default is 0 only which means
    when calculating a layer in this level, take the layerID and +0 to it
    and use that layerID from the previous level as input.  If instead the
    inputLayerIDs were [0,1] then when calculating layer x in this level use
    layers x+0 and x+1 from the previous level as input to the filter.
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
    self.layers = layers
    #Debug
    print "\n"+self.name
    for layer in self.layers:
      print layer
  
  def getMaxLayerValue(self):
    """ doc """
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
    #print "inferring "+self.name+"..."
    for layer in self.layers:
      self.filter.computeLayer(layer)
    
    #TODO: create GaborFilterC.py for python interface into hmaxc.GaborFilterC
  

class ImageLevel(Level):
  """ doc """
  
  def __init__(self, network, name, index, filter):
    Level.__init__(self, network, name, index, filter)
    
  def computeLevel(self, inputImage):
    """
    doc
    """
    assert inputImage.size==(self.layers[0].xSize, self.layers[0].ySize)
    self.layers[0].setLayerData(Util.convertPILtoNumpy(inputImage, False))
    
    #print "inferring "+self.name+"..."
    for layer in self.layers[1:]:
      ri = inputImage.resize((layer.xSize,layer.ySize), Image.BILINEAR)
      layer.setLayerData(Util.convertPILtoNumpy(ri, False))
  
  