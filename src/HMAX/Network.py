'''
Created on May 3, 2011

@author: Barry Maturkanich

HMAX is an algorithm inspired by circuits in the visual areas of 
the neocortex, mostly the feed-forward path through the ventral stream
which includes V1, V2, V4, and IT.

The goal then is to be able to take an input image and decide which of
several classes of objects are present in the image.  Or at least be
able to say how closely an input image matches previously learned
example images.

HMAX only models the 'spatial pooling' aspects and does not account at all
for any time/temporal related abilities.  In the real brain temporal
processing is a central component and must be present to account for any
sort of real interaction, however HMAX lets us simplify one specific
processing aspect in the neocortical visual system to achieve a very 
limited yet very useful visual algorithm.  HMAX also serves as something
of a starting point for later building in temporal and/or top-down 
processing as we research over time.

HMAX uses scale-space and a spatial hierarchy to perform processing
on small sub-components of the image in multiple image scales/sizes.

The hierarchy consists of multiple Levels, with lower levels feeding
data into the higher levels, one level to the next.  The bottom-most
level takes in the original input image while the top-most level
performs the final classification decision.

Each level will consist of one or more Layers.  Each layer is intended
to handle differently scaled sizes of the original input image in order
to perform a sort of parallel processing of multiple object sizes.
As we ascend the hierarchy we slowly combine the scale layers by 
selecting the best responses between 2 neighboring scales resulting 
in an overall best response across many sizes.  This gives an increased
invarience to size when performing classification.

The HMAX algorithm used in this code is primarily based on the 
following academic paper: 
Jim Mutch and David G. Lowe.
Object class recognition and localization using sparse features 
with limited receptive fields. 2008.
'''

import time
import numpy
import HMAX
from HMAX.Layer import Layer, LayerC, LayerS2, LayerC2
from HMAX.Level import Level, ImageLevel
from HMAX.GaborFilter import GaborFilter, GaborFilterC
from HMAX.MaxFilter import MaxFilter, MaxFilterC
from HMAX.GRBFFilter import GRBFFilter, GRBFFilterC
from HMAX.GlobalMaxFilter import GlobalMaxFilter

class Network(object):
  """
  Represent an entire HMAX Network (scale-space hierarchy).
  The network will take a single image as input and perform
  hierarchical processing to identify feature components and
  then perform a classification to try and identify an object
  class for the entire image.
  """
  
  def __init__(self, baseSize, scaleCount=2, thetaCount=8):
    """
    @param baseSize: tuple (width,height) pixel size of base input image.
    @param scaleCount: number of image scales to generate for the network.
    @param thetaCount: number of gabor angle thetas to include in the network.
    """
    gaborSize = 9
    learnSize = GRBFFilter.MAX_PATCHES
    
    piInc = numpy.pi / thetaCount
    self.thetas = []
    for i in xrange(thetaCount):
      self.thetas.append(piInc*i)
    
    #Create the level filters
    s1Filter = GaborFilterC(self.thetas, size=gaborSize,lam=4.6,sigma=3.6)
    c1Filter = MaxFilterC(2,8)
    s2Filter = GRBFFilterC()
    c2Filter = GlobalMaxFilter(scaleCount/2)
    
    #Create the levels, passing in their respective filters
    self.levels = []
    self.levels.append(ImageLevel(self, "SI Input", 0, None))
    self.levels.append(Level(self, "S1 Gabor", 1, s1Filter))
    self.levels.append(Level(self, "C1", 2, c1Filter))
    self.levels.append(Level(self, "S2", 3, s2Filter))
    self.levels.append(Level(self, "C2 SVM Results", 4, c2Filter))
    
    #Create all the layers for each of the levels
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
      c2Layers.append(LayerC2(self.levels[4], xySize, learnSize, xyStart, xySpace, [pl]))

    #finally pass the created layers into each of the levels
    self.levels[0].setLayers(siLayers)
    self.levels[1].setLayers(s1Layers)
    self.levels[2].setLayers(c1Layers)
    self.levels[3].setLayers(s2Layers)
    self.levels[4].setLayers(c2Layers)
  
  @property
  def S1(self):
    return self.levels[1].filter
  
  @property
  def S2(self):
    return self.levels[3].filter
  
  @property
  def C2(self):
    return self.levels[4].filter
  
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
    if HMAX.DEBUG:
      print "Level 0 took %dms" % ((time.clock()-t) * 1000.0)
    
    #if learning is enabled for S2, do not compute levels beyond it
    maxLevel = len(self.levels)
    if self.S2.isLearning:
      maxLevel = 4
    
    for level in self.levels[1:maxLevel]:
      t = time.clock()
      level.computeLevel()
      if HMAX.DEBUG:
        print "Level %d took %dms" % (level.index, (time.clock()-t) * 1000.0)
  


def mapScaledPixels(baseSize, factor, ranges):
  """
  Generate a scaled version of the base image size provided such that the new
  scaled image size has an identical retinal space mapping as the original.
  Use the factor parameter to decide how much to scale the original image size.
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
  Given a description of previous layer sizes (pSizes,pStarts,pSpaces), generate
  sizes for the next layer using the unit width/step guidance parameters.
  Basically given an input layer and suggestion for what cell sizes we want for
  the next layer, generate how many cells we will need and their size in retinal
  space for the new layer.
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
