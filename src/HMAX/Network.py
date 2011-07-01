'''
Created on May 3, 2011

@author: barry

HMAX is an algorithm inspired by circuits in the visual areas of 
the neocortex, mostly the feed-forward path through the ventral stream
which includes V1, V2, V4, and IT.

It only models the 'spatial pooling' aspects and does not account at all
for any time/temporal related abilities.  In the real brain temporal
processing is a central component and must be present to account for any
sort of real interaction, however HMAX lets us simplify one specific
processing aspect in the neocortical visual system to achieve a very 
limited yet very useful visual algorithm.  HMAX also serves as something
of a starting point for later building in temporal and/or top-down 
processing as we research over time.

HMAX uses scale-space and a spatial hierarchy to perform processing
on small sub-components of the image in multiple image scales/sizes.

To use, we need to create an HMAX object that takes:

1) a set of image dimensions/sizes where the largest size corresponds
   to the size of the native input images and all smaller sizes will
   be the native image scaled down.
2) 
'''

import time
import numpy
import Util
from PIL import Image
from HMAX.Layer import Layer, LayerC, LayerS2
from HMAX.Level import Level, ImageLevel
from HMAX.GaborFilter import GaborFilter, GaborFilterC
from HMAX.MaxFilter import MaxFilter, MaxFilterC
from HMAX.GRBFFilter import GRBFFilter
from HMAX.GlobalMaxFilter import GlobalMaxFilter

class Network(object):
  """
  Represent a single HMAX Network (scale-space hierarchy).
  """
  
  def __init__(self, baseSize, scaleCount=6, thetaCount=4):
    """
    @param baseSize: tuple (width,height) pixel size of base input image.
    @param scaleCount: number of image scales to generate for the network.
    @param thetaCount: number of gabor angle thetas to include in the network.
    """
    gaborSize = 9
    learnSize = 100
    
    piInc = numpy.pi / thetaCount
    self.thetas = []
    for i in xrange(thetaCount):
      self.thetas.append(piInc*i)
    
    s1Filter = GaborFilterC(self.thetas, size=gaborSize,lam=4.6,sigma=3.6)
    c1Filter = MaxFilterC(2,8)
    s2Filter = GRBFFilter()
    c2Filter = GlobalMaxFilter(scaleCount/2, self.thetas)
    
    self.levels = []
    self.levels.append(ImageLevel(self, "SI", 0, None))
    self.levels.append(Level(self, "S1 (Gabor)", 1, s1Filter))
    self.levels.append(Level(self, "C1", 2, c1Filter))
    self.levels.append(Level(self, "S2", 3, s2Filter))
    self.levels.append(Level(self, "C2", 4, c2Filter))
    
    siLayers = []
    factor = numpy.power(2,0.25)
    scaleSize = numpy.array([-0.5,0.5])
    for s in xrange(1,scaleCount+1):
      fac = numpy.power(factor,(s-1))
      xySize, xyStart, xySpace = mapScaledPixels(baseSize, fac, scaleSize*zip(baseSize))
      siLayers.append(Layer(self.levels[0], xySize, 1, xyStart, xySpace))
    
    s1Layers = []
    for pl in siLayers:
      p = [(pl.xSize,pl.ySize), pl.xyStart, pl.xySpace]
      xySize, xyStart, xySpace = mapInt(p[0], p[1], p[2], gaborSize, 1)
      s1Layers.append(LayerC(self.levels[1], xySize, thetaCount, xyStart, xySpace, [pl]))
      
    rfSize, rfStep = gaborSize-1, gaborSize/2
    c1Layers = []
    #We lose one scale because we pool over two adjacent scales.
    for pi in xrange(0,len(s1Layers)-1):
      pl, pl2 = s1Layers[pi], s1Layers[pi+1]
      p = [(pl.xSize,pl.ySize), pl.xyStart, pl.xySpace]
      xySize, xyStart, xySpace = mapInt(p[0], p[1], p[2], rfSize, rfStep)
      c1Layers.append(LayerC(self.levels[2], xySize, thetaCount, xyStart, xySpace, [pl,pl2]))
      
    rfSize, rfStep = 4, 1
    s2Layers = []
    for pl in c1Layers:
      p = [(pl.xSize,pl.ySize), pl.xyStart, pl.xySpace]
      xySize, xyStart, xySpace = mapInt(p[0], p[1], p[2], rfSize, rfStep)
      s2Layers.append(LayerS2(self.levels[3], xySize, learnSize, xyStart, xySpace, [pl]))
    
    c2Layers = []
    for pl in s2Layers:
      xySize, xyStart, xySpace = ((1,1),(0,0),(1,1))
      c2Layers.append(Layer(self.levels[4], xySize, learnSize, xyStart, xySpace, [pl]))

    self.levels[0].setLayers(siLayers)
    self.levels[1].setLayers(s1Layers)
    self.levels[2].setLayers(c1Layers)
    self.levels[3].setLayers(s2Layers)
    self.levels[4].setLayers(c2Layers)
    
    self.setLearning()
  
  def getLastAccuracy(self):
    return self.levels[4].filter.accuracy
  
  def setLearning(self, learnOn=True):
    """ doc """
    self.levels[4].filter.isLearning = learnOn
  
  def isLearningS2(self):
    return self.levels[3].filter.isLearning
  
  def inference(self, image):
    """
    Run the specified input image through a single inference pass of this 
    HMAX Network.  Each network level will be computed sequentially with results
    from each previous level being used as input to subsequent levels.
    @param image: the raw input image assumed to be a PIL image with a size
    that matches the defined baseSize for this network.
    """
    t = time.clock()
    self.levels[0].computeLevel(image) #Level0 is special, needs input image
    print "Level 0 took %dms" % ((time.clock()-t) * 1000.0)
    
    #if learning is enabled for S2, do not compute levels beyond it
    maxLevel = len(self.levels)
    if self.isLearningS2():
      maxLevel = 4
    
    for level in self.levels[1:maxLevel]:
      t = time.clock()
      level.computeLevel()
      print "Level %d took %dms" % (level.index, (time.clock()-t) * 1000.0)
  


def mapScaledPixels(baseSize, factor, ranges):
  """
  @param baseSize: tuple of (x,y) input image size.
  @param factor: multiplier factor to scale retinal space cells compared to input image.
  @param ranges: numpy matrix of range arrays for retinal space in x and y directions.
  """
  nSpaces = []
  nStarts = []
  nSizes = []
  
  for i in xrange(len(baseSize)):
    bSize = baseSize[i]
    range = ranges[i]
    
    drange = abs(range[0]-range[1])
    nSpace = drange / bSize * factor
    
    if bSize % 2 == 1:
      nSize = max(0, 2 * numpy.floor((drange - nSpace) / (2 * nSpace)) + 1)
    else:
      nSize = max(0, 2 * numpy.floor(drange / (2* nSpace)))
    
    nStart = numpy.mean(range) - 0.5 * nSpace * (nSize - 1)
    
    nSpaces.append(nSpace)
    nStarts.append(nStart)
    nSizes.append(int(nSize))
    
  return nSizes, nStarts, nSpaces

def mapInt(pSizes, pStarts, pSpaces, rfSize, rfStep, parity=[]):
  """
  @param rfSize: unit width in previous layer units.
  @param rfStep: unit step size in previous layer units.
  @param parity: 0 if you prefer an even-sized output, 1 if odd, [] if you don't care.
  """
  nSpaces = []
  nStarts = []
  nSizes = []
  
  for i in xrange(len(pSizes)):
    pSize = pSizes[i]
    pStart = pStarts[i]
    pSpace = pSpaces[i]
    
    pCenter = pStart + 0.5 * pSpace * (pSize - 1)
    
    nSpace = pSpace * rfStep
    
    nSize1 = max(0, 2*numpy.floor((pSize-rfSize       ) / (2*rfStep)) + 1)
    nSize0 = max(0, 2*numpy.floor((pSize-rfSize-rfStep) / (2*rfStep)) + 2)
    
    if pSize % 2 == rfSize % 2:
      if rfStep % 2 == 0:
        #We can place a unit in the center, or not.
        if parity==1 or (len(parity)==0 and (nSize1 >= nSize0)):
            nSize = nSize1
        else:
            nSize = nSize0
      else:
        #We must place a unit in the center.  The result will have an odd number of units.
        nSize = nSize1
    else:
      #We cannot place a unit in the center, so the result will have an even number
      # of units, and we must place a unit on either side of the center, at the 
      # same distance from the center.  This is only possible if rfStep is odd.
      #This really requires a diagram to see.  There are two cases to consider: 
      # pSize odd, rfSize even and vice-versa.
      nSize = nSize0;
      if (nSize > 0) and (rfStep%2 == 0):
        raise Exception('when the result layer has an even number of units, rfStep must be odd')
    
    nStart = pCenter - 0.5 * nSpace * (nSize - 1)
    
    nSpaces.append(nSpace)
    nStarts.append(nStart)
    nSizes.append(int(nSize))
  
  return nSizes, nStarts, nSpaces

#// Initialize filters.
#
#    GaborFilter fs1(11, 0.3f, 5.6410f, 4.5128f, 12); const int s1SStep = 1;
#    MaxFilter   fc1(2, 10)                         ; const int c1SStep = 1;
#    GRBFFilter  fs2(4, 1.0f, prhs[0])              ; const int s2SStep = 1;
#    GMaxFilter  fc2(6)                             ; const int c2SStep = 5;
#
#    // Initialize network structure.
#
#    // NOTE: the hardcoded numbers below were generated by the script more/example_generate.m.  I've done things this
#    // way because making the code more general introduces more levels of abstraction, and hmin's purpose in life is to
#    // be easily understood.  For all the generality you could ever want, see the full hmax package.
#
#    // The first two numbers for each layer are the sizes of its spatial (Y, X) and feature (F) dimensions.  The two
#    // decimal numbers determine the coordinates of each (Y, X) grid point in a real-valued retinal coordinate system
#    // which is consistent across layers.  This is explained in more detail in the file "layer.h".  Note we assume here
#    // that layers are square, i.e., their two spatial dimensions are equal.
#
#    const int nsi = 12;
#    Layer *si[nsi];
#    si[ 0] = new Layer(256, 1           , -127.5000000000000000f,   1.0000000000000000f);
#    si[ 1] = new Layer(214, 1           , -126.6505577477897901f,   1.1892071150027210f);
#    si[ 2] = new Layer(180, 1           , -126.5721138323919917f,   1.4142135623730949f);
#    si[ 3] = new Layer(152, 1           , -126.9753587033108744f,   1.6817928305074288f);
#    si[ 4] = new Layer(128, 1           , -126.9999999999999858f,   1.9999999999999998f);
#    si[ 5] = new Layer(106, 1           , -124.8667470752856872f,   2.3784142300054416f);
#    si[ 6] = new Layer( 90, 1           , -125.8650070512054242f,   2.8284271247461894f);
#    si[ 7] = new Layer( 76, 1           , -126.1344622880571649f,   3.3635856610148576f);
#    si[ 8] = new Layer( 64, 1           , -125.9999999999999716f,   3.9999999999999991f);
#    si[ 9] = new Layer( 52, 1           , -121.2991257302775239f,   4.7568284600108832f);
#    si[10] = new Layer( 44, 1           , -121.6223663640861190f,   5.6568542494923779f);
#    si[11] = new Layer( 38, 1           , -124.4526694575497032f,   6.7271713220297134f);
#
#    const int ns1 = 12;
#    Layer *s1[ns1];
#    s1[ 0] = new Layer(246, fs1.FCount(), -122.5000000000000000f,   1.0000000000000000f);
#    s1[ 1] = new Layer(204, fs1.FCount(), -120.7045221727761799f,   1.1892071150027210f);
#    s1[ 2] = new Layer(170, fs1.FCount(), -119.5010460205265161f,   1.4142135623730949f);
#    s1[ 3] = new Layer(142, fs1.FCount(), -118.5663945507737225f,   1.6817928305074288f);
#    s1[ 4] = new Layer(118, fs1.FCount(), -116.9999999999999858f,   1.9999999999999998f);
#    s1[ 5] = new Layer( 96, fs1.FCount(), -112.9746759252584809f,   2.3784142300054416f);
#    s1[ 6] = new Layer( 80, fs1.FCount(), -111.7228714274744874f,   2.8284271247461894f);
#    s1[ 7] = new Layer( 66, fs1.FCount(), -109.3165339829828753f,   3.3635856610148576f);
#    s1[ 8] = new Layer( 54, fs1.FCount(), -105.9999999999999716f,   3.9999999999999991f);
#    s1[ 9] = new Layer( 42, fs1.FCount(),  -97.5149834302231113f,   4.7568284600108832f);
#    s1[10] = new Layer( 34, fs1.FCount(),  -93.3380951166242312f,   5.6568542494923779f);
#    s1[11] = new Layer( 28, fs1.FCount(),  -90.8168128474011240f,   6.7271713220297134f);
#
#    const int nc1 = 11;
#    Layer *c1[nc1];
#    c1[ 0] = new Layer( 47, fs1.FCount(), -115.0000000000000000f,   5.0000000000000000f);
#    c1[ 1] = new Layer( 39, fs1.FCount(), -112.9746759252584951f,   5.9460355750136049f);
#    c1[ 2] = new Layer( 33, fs1.FCount(), -113.1370849898475939f,   7.0710678118654746f);
#    c1[ 3] = new Layer( 27, fs1.FCount(), -109.3165339829828895f,   8.4089641525371448f);
#    c1[ 4] = new Layer( 21, fs1.FCount(),  -99.9999999999999858f,   9.9999999999999982f);
#    c1[ 5] = new Layer( 17, fs1.FCount(),  -95.1365692002176644f,  11.8920711500272080f);
#    c1[ 6] = new Layer( 15, fs1.FCount(),  -98.9949493661166287f,  14.1421356237309475f);
#    c1[ 7] = new Layer( 11, fs1.FCount(),  -84.0896415253714480f,  16.8179283050742896f);
#    c1[ 8] = new Layer(  9, fs1.FCount(),  -79.9999999999999858f,  19.9999999999999964f);
#    c1[ 9] = new Layer(  7, fs1.FCount(),  -71.3524269001632518f,  23.7841423000544161f);
#    c1[10] = new Layer(  5, fs1.FCount(),  -56.5685424949237756f,  28.2842712474618878f);
#
#    const int ns2 = 11;
#    Layer *s2[ns2];
#    s2[ 0] = new Layer( 44, fs2.FCount(), -107.5000000000000000f,   5.0000000000000000f);
#    s2[ 1] = new Layer( 36, fs2.FCount(), -104.0556225627380798f,   5.9460355750136049f);
#    s2[ 2] = new Layer( 30, fs2.FCount(), -102.5304832720493806f,   7.0710678118654746f);
#    s2[ 3] = new Layer( 24, fs2.FCount(),  -96.7030877541771616f,   8.4089641525371448f);
#    s2[ 4] = new Layer( 18, fs2.FCount(),  -84.9999999999999858f,   9.9999999999999982f);
#    s2[ 5] = new Layer( 14, fs2.FCount(),  -77.2984624751768479f,  11.8920711500272080f);
#    s2[ 6] = new Layer( 12, fs2.FCount(),  -77.7817459305202163f,  14.1421356237309475f);
#    s2[ 7] = new Layer(  8, fs2.FCount(),  -58.8627490677600136f,  16.8179283050742896f);
#    s2[ 8] = new Layer(  6, fs2.FCount(),  -49.9999999999999929f,  19.9999999999999964f);
#    s2[ 9] = new Layer(  4, fs2.FCount(),  -35.6762134500816259f,  23.7841423000544161f);
#    s2[10] = new Layer(  2, fs2.FCount(),  -14.1421356237309439f,  28.2842712474618878f);
#
#    const int nc2 = 2;
#    Layer *c2[nc2];
#    c2[ 0] = new Layer(  1, fs2.FCount(),    0.0000000000000000f,   1.0000000000000000f);
#    c2[ 1] = new Layer(  1, fs2.FCount(),    0.0000000000000000f,   1.0000000000000000f);
#
#    // Load input (a pre-scaled image pyramid).
#
#    if (mxGetClassID(prhs[1]) != mxCELL_CLASS) mexErrMsgTxt("input is not a cell array");
#    if (mxGetNumberOfElements(prhs[1]) != nsi) mexErrMsgTxt("input has the wrong number of elements");
#
#    for (int s = 0; s < nsi; s++) si[s]->SetLayer(mxGetCell(prhs[1], s));
#
#    // Compute!
#
#    for (int s = 0; s < ns1; s++) fs1.ComputeLayer(si + s * s1SStep, s1[s]);
#    for (int s = 0; s < nc1; s++) fc1.ComputeLayer(s1 + s * c1SStep, c1[s]);
#    for (int s = 0; s < ns2; s++) fs2.ComputeLayer(c1 + s * s2SStep, s2[s]);
#    for (int s = 0; s < nc2; s++) fc2.ComputeLayer(s2 + s * c2SStep, c2[s]);
#
#    // Get output.
#
#    plhs[0] = mxCreateCellMatrix(1, nc2);
#
#    for (int s = 0; s < nc2; s++) mxSetCell(plhs[0], s, c2[s]->GetLayer());