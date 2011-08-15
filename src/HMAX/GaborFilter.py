"""
Created on Apr 28, 2011

@author: Barry Maturkanich

Implementation of Gabor filters (S1) used by the HMAX algorithm.
The Gabor filter is used to detect how strongly a patch of pixels
matches lines of particular orientations.  The Gabor filter is
commonly used to approximate the V1 area of neocortex.

The equation to generate a Gabor filter is as follows:
G(x,y) = exp(-(X^2 + r^2*Y^2) / 2sg^2) * cos(2pi*X / ld)

where:
 X = x*cos(theta) - y*sin(theta)
 Y = x*sin(theta) + y*cos(theta)
 r = aspectRatio
 sg = sigma (effective width)
 ld = lamda (wavelength)

The response of a patch of pixels X to a particular S1/Gabor 
filter is given by:
R(X,G) = | sum(Xi*Gi) / sqrt(sum(Xi^2)) |

Some common values used for various gabor filter sizes are as
follows (obtained through trial-and-error experimentation):
size --- sigma --- lambda -- C1
  7       2.8       3.5 
  9       3.6       4.6     8x8 4over
 11       4.5       5.6
 13       5.4       6.8     10x10 5over
 15       6.3       7.9
 17       7.3       9.1     12x12 6over
"""

import hmaxc
import math
import numpy
from HMAX.LevelFilter import LevelFilter

class GaborFilter(LevelFilter):
  """
  GaborFilter class
  fs1(11, 0.3f, 5.6410f, 4.5128f, 12)
  GaborFilter(int yxCount, float aspect, float lambda, float sigma, int fCount);
  """
  
  def __init__(self, thetas, size=11, lam=5.6, sigma=4.5, aspect=0.3):
    """
    @param size: the integer size (length and width) for this filter.
    @param thetas: the set of angle orientations, in radians, to use for this filter.
    @param lam: the lambda wavelength this filter is tuned with.
    @param sigma: the effective width sigma to tune the filter to.
    @param aspect: the aspect ratio to tune the filter to.
    """
    assert size % 2 == 1 #size must be an odd number
    s2 = size / 2
    aspectSqr = aspect**2
    sigmaSqr2 = 2*(sigma**2)
    pi2 = math.pi*2
    
    self.thetas = thetas
    self.gabors = {}
    self.size = size
    
    mat = numpy.zeros((size,size))
    
    for theta in thetas:
      for j in xrange(-s2, s2+1):
        for i in xrange(-s2, s2+1):
          y = (i * math.sin(theta)) + (j * math.cos(theta))
          x = (i * math.cos(theta)) - (j * math.sin(theta))
          
          if math.sqrt(x*x+y*y) <= 0.5 * size:
            e = math.exp(-(x*x + (aspectSqr*(y*y))) / sigmaSqr2)
            e *= math.cos(pi2*x / lam)
          else:
            e = 0.0
          mat[i+s2][j+s2] = e
      
      mean = numpy.mean(mat)
      stdv = numpy.std(mat)
      self.gabors[theta] = ((mat-mean) / stdv)
  
  @property
  def thetaCount(self):
    return len(self.thetas)
  
  def computeUnit(self, layerInputs, pos, f):
    """
    Run the GaborFilter on the input data from the previous network layer
    at the specified position. The result value will be returned and is
    expected to then be stored in the S1 network layer.
    @param layerInputs: layer containing a numpy matrix representing 
    the input gray-scale image.
    @param pos: (x,y) tuple position in the image to center the filter on.
    @param f: the feature index (in this case the theta index) to run.
    """
    cx,cy = pos
    layerInput = layerInputs[0]
    
    #Get the boundary indicies for the part of the image to filter,
    #if any part of the filter spills over edge of image, cannot calculate
    (xi1,xi2), xOK = layerInput.getXRFNear(cx, self.size)
    if not xOK:
      return 0
    (yi1,yi2), yOK = layerInput.getYRFNear(cy, self.size)
    if not yOK:
      return 0
    
    res = 0.0
    len = 0.0
    gabor = self.gabors[self.thetas[f]]
    
    for xi in xrange(xi1, xi2+1):
      for yi in xrange(yi1, yi2+1):
        w = gabor[xi-xi1][yi-yi1]
        v = layerInput.get((xi,yi), 0)
        res += w*v
        len += v*v
    
    res = abs(res)
#    if len > 0.0:
#      res /= math.sqrt(len) #res /= 255.0
    return res
  
  def getInputBoundBox(self, layer, rbbox):
    """
    Determine the pixel bounding box corresponding to the input retinal-space
    bounding box.  This method is primarily used to generate feedback used
    in the UI to render input sources for higher layer results.
    @param layerInput: the layer the filter will read input values from.
    @param rbbox: the retinal bound box within the current layer.
    @return tuple (x,y, w,h) bounding box pixel coordinates.
    """
    cx,cy = rbbox[0:2]
    
    #Get the boundary indicies for the part of the image to filter,
    #if any part of the filter spills over edge of image, cannot calculate
    (xi1,xi2), xOK = layer.getXRFNear(cx, self.size)
    (yi1,yi2), yOK = layer.getYRFNear(cy, self.size)
    xi, yi = min(xi1,xi2), min(yi1,yi2)
    
    cx,cy = rbbox[0]+rbbox[2], rbbox[1]+rbbox[3]
    (xi1,xi2), xOK = layer.getXRFNear(cx, self.size)
    (yi1,yi2), yOK = layer.getYRFNear(cy, self.size)
    xi2,yi2 = max(xi1,xi2), max(yi1,yi2)
    
    return (xi,yi, xi2-xi, yi2-yi)


class GaborFilterC(GaborFilter):
  """
  GaborFilterC is a python wrapper for the C++ hmaxc.GaborFilterC object.
  The C++ implementation runs the same algorithm but with much better
  performance.
  """
  
  def __init__(self, thetas, size=11, lam=5.6, sigma=4.5, aspect=0.3):
    """
    @param size: the integer size (length and width) for this filter.
    @param thetas: the set of angle orientations, in radians, to use for this filter.
    @param lam: the lambda wavelength this filter is tuned with.
    @param sigma:
    @param aspect: the aspect ratio.
    """
    #GaborFilterC(float thetas[], int thetaCount, int size=11, 
    #             float lam=5.6, float sigma=4.5, float aspect=0.3);
    self.size = size
    cthetas = hmaxc.floatCArray(len(thetas))
    for i in xrange(len(thetas)):
      #print "pyTheta"+str(i)+": ",thetas[i]
      cthetas[i] = thetas[i]
    self.cGabor = hmaxc.GaborFilterC(cthetas, len(thetas), size, lam, sigma, aspect)
  
  @property
  def thetaCount(self):
    return self.cGabor.thetaCount()
  
  def computeLayer(self, layerOut):
    """
    Override computeLayer so we call into C++ code for fast performance.
    @param layer: the output HmaxLayer to store results in.
    """
    #computeLayer(float* layerIn, int wi, int hi,LayerC* layerOut)
    layerIn = layerOut.inputLayers[0]
    wi, hi = layerIn.xSize, layerIn.ySize
    layerInCArray = layerIn.getLayerDataAsCArray()
    
    self.cGabor.computeLayer(layerInCArray, wi,hi, layerOut.cLayer)
    layerOut.setLayerDataFromCArray()



