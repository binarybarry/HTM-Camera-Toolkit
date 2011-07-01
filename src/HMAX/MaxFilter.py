'''
Created on May 3, 2011

@author: barry
'''

import hmaxc
from HMAX.LevelFilter import LevelFilter

class MaxFilter(LevelFilter):
  """ 
  Performs a per-feature local maximum over position and scale in 
  one or more input layers. 
  """
  
  def __init__(self, sCount, xyCount):
    """
    Create a new filter of this type.
    @param sCount: number of scales over which to pool.
    @param xyCount: number of grid positions (largest scale) over which to pool
    """
    self.sCount = sCount
    self.xyCount = xyCount
    
  def computeUnit(self, layerInputs, pos, f):
    """ 
    @param layerInputs: assume this is tuple of sCount inputLayers.
    """
    #Re-express YXCOUNT as a distance in real-valued retinal coordinates.
    xr = layerInputs[0].xySpace[0] * 0.5 * self.xyCount
    yr = layerInputs[0].xySpace[1] * 0.5 * self.xyCount
    xc,yc = pos
    
    #Now for each input layer (i.e. each scale) perform a local max 
    #over position for feature F.
    res = 0 #TODO better start value?
    for s in xrange(self.sCount):
      (xi1,xi2), xOK = layerInputs[s].getXRFDist(xc,xr)
      (yi1,yi2), yOK = layerInputs[s].getYRFDist(yc,yr)
      
      for xi in xrange(xi1,xi2+1):
        for yi in xrange(yi1,yi2+1):
          v = layerInputs[s].get((xi,yi), f)
          res = max(res, v)
    
    return res
  
  def getInputBoundBox(self, layer, rbbox):
    """
    @param layerInput: the layer the filter will read input values from.
    @param rbbox: the retinal bound box within the current layer.
    @return tuple (x,y, w,h) bounding box pixel coordinates.
    """
    #Re-express YXCOUNT as a distance in real-valued retinal coordinates.
    xr = layer.xySpace[0] * 0.5 * self.xyCount
    yr = layer.xySpace[1] * 0.5 * self.xyCount
    
    #Get the bounding box input coordinates
    xc,yc = rbbox[0:2]
    (xi1,xi2), xOK = layer.getXRFDist(xc,xr)
    (yi1,yi2), yOK = layer.getYRFDist(yc,yr)
    xi, yi = min(xi1,xi2), min(yi1,yi2)
    
    xc,yc = rbbox[0]+rbbox[2], rbbox[1]+rbbox[3]
    (xi1,xi2), xOK = layer.getXRFDist(xc,xr)
    (yi1,yi2), yOK = layer.getYRFDist(yc,yr)
    xi2,yi2 = max(xi1,xi2), max(yi1,yi2)
    
    return (xi,yi, xi2-xi, yi2-yi)


class MaxFilterC(MaxFilter):
  """
  MaxFilterC is a python wrapper for the C++ hmaxc.MaxFilterC object.
  Performs a per-feature local maximum over position and scale in 
  one or more input layers. 
  """
  
  def __init__(self, sCount, xyCount):
    """
    Create a new filter of this type.
    @param sCount: number of scales over which to pool.
    @param xyCount: number of grid positions (largest scale) over which to pool
    """
    MaxFilter.__init__(self, sCount, xyCount)
    
    self.cMaxFilter = hmaxc.MaxFilterC(sCount, xyCount)
    
  def computeLayer(self, layerOut):
    """
    Override computeLayer so we call into C++ code for fast performance.
    @param layer: the output HmaxLayer to store results in.
    """
    #computeLayer(const LayerC* layersIn, LayerC* layerOut)
    lay1, lay2 = layerOut.inputLayers
    self.cMaxFilter.computeLayer(lay1.cLayer, lay2.cLayer, layerOut.cLayer)
    layerOut.setLayerDataFromCArray()

