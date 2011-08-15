"""
Created on May 3, 2011

@author: Barry Maturkanich

This file contains the definition of an abstract filter used by
the layers within a common hierarchical level in an HMAX Network.

All filters must be able to take data from a bottom-up input layer
and process/filter it in order to produce output that will be sent
to the layers in the next level of network hierarchy.

Filters must be subclasses of the LevelFilter and implement the
computeUnit method to produce their desired outputs.
The filter must also be able to determine the source of inputs from
its bottom-up input layer for a particular position if requested.
"""

class LevelFilter(object):
  """
  Abstract Layer Filter class.  Takes one or more HMAX Network Layers as input
  and produces one Layer worth of output.
  """
  
  def __init__(self):
    """ Nothing to construct by default. """
    
  def computeLayer(self, layer):
    """
    Compute an entire set of results using the specified output layer.
    Each layer is already connected to its input layers during network
    construction so this method will simply loop over each discrete
    output layer cell and compute a value using the filter-defined
    compute method (which has access to the entire matrix of input
    layer values that can be read as each filter deems necessary).
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
    Run the Filter on the input data from the previous network layer
    at the specified position. The result value will be returned and is
    expected to then be stored in the current output network layer.
    @param layerInputs: list of layer inputs this filter will read from.
    @param pos: coordinate position in real-valued space.
    @param f: layer feature index
    """
    assert False #subclasses must override this method
    
  def getInputBoundBox(self, layerInput, rbbox):
    """
    Determine the pixel bounding box corresponding to the input retinal-space
    bounding box.  This method is primarily used to generate feedback used
    in the UI to render input sources for higher layer results.
    @param layerInput: the layer the filter will read input values from.
    @param rbbox: the retinal bound box within the current layer.
    @return tuple (x,y, w,h) bounding box pixel coordinates.
    """
    assert False #subclasses must override this method
