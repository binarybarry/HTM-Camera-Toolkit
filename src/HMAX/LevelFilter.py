'''
Created on May 3, 2011

@author: barry
'''

class LevelFilter(object):
  """
  Abstract Layer Filter class.  Takes one or more HMAX Network Layers as input
  and produces one Layer worth of output.
  """
  
  def __init__(self):
    """ doc """
    
  def computeLayer(self, layer):
    """
    @param layer: the output HmaxLayer to store results in.
    """
    out = layer
    for f in xrange(out.fSize):
      
      for xi in xrange(out.xSize):
        xc = out.xCenter(xi)
        
        for yi in xrange(out.ySize):
          
          yc = out.yCenter(yi)
          val = self.computeUnit(out.inputLayers, (xc,yc), f)
          out.set((xi,yi), f, val)
          
    
  def computeUnit(self, layerInputs, pos, f):
    """
    @param layerInputs: list of layer inputs this filter will read from.
    @param pos: coordinate position in real-valued space.
    @param f: feature index
    """
    assert False #subclasses must override this method
    
  def getInputBoundBox(self, layerInput, rbbox):
    """
    @param layerInput: the layer the filter will read input values from.
    @param rbbox: the retinal bound box within the current layer.
    @return tuple (x,y, w,h) bounding box pixel coordinates.
    """
    assert False #subclasses must override this method
