'''
Created on May 5, 2011

@author: barry
'''

import random
import numpy
from HMAX.LevelFilter import LevelFilter

class S2Cell(object):
  """ doc """
  
  def __init__(self, s4x4):
    self.s4x4 = s4x4 #numpy(4x4) of (vmax,f) of C1 inputs
    self.__sumv = numpy.sum(s4x4[:,0]) #sum(vmax) in s4x4
    self.rpos = (0,0) #(xi,yi) relative integer layer position
    
  @property
  def sumv(self):
    return self.__sumv
    


class GRBFFilter(LevelFilter):
  """
  classdocs
  """
  MIN_NONZERO_PCT = 0.25 #minimum % of values that must be non-zero to learn patch
  SPATIAL_POOL_DIST = 0.8#learned patches must have RBF dist less than this

  def __init__(self, xyCountMin=4, sigma=1.0):
    """
    @param xyCountMin: edge size of the smallest feature to be learned.
    @param sigma: Standard deviation of the gaussian applied to the distance 
    between the template and the input patch.
    """
    self.xyCountMin = xyCountMin
    self.sigma = sigma
    self.learned = [] #list of numpyArrays for learned patches
    self.isLearning = False
    self.lastLearned = None
    random.seed(420)
  
  def computeLayer(self, layerOut):
    """
    @param layer: the output HmaxLayer to store results in.
    """
    out = layerOut
    layerIn = out.inputLayers[0]
    
    arrayC1 = self.buildCompositeC1(layerIn, layerOut)
    
    if self.isLearning:
      self.learnPatch(layerIn, arrayC1)
    else:
      out = layerOut
      for f in xrange(len(self.learned)):
        for xi in xrange(out.xSize):
          xc = out.xCenter(xi)
          for yi in xrange(out.ySize):
            yc = out.yCenter(yi)
            val = self.computeUnit(out.inputLayers, (xc,yc), f)
            out.set((xi,yi), f, val)
    
    #Calculate the arrayS2 used for rendering the state of the layer
    for xi in xrange(out.xSize):
      xc = out.xCenter(xi)
      for yi in xrange(out.ySize):
        yc = out.yCenter(yi)
        s2cell = self.getS2Cell(arrayC1, layerIn, (xc,yc))
#        out.set((xi,yi), 0, s2cell.sumv)
        out.arrayS2[xi][yi] = s2cell
  
  def buildCompositeC1(self, layerIn, layerOutS2):
    """ 
    Build the composite C1 used as input to S2. 
    """
    for xi in xrange(layerIn.xSize):
      for yi in xrange(layerIn.ySize):
        
        vmax = layerIn.get((xi,yi), 0)
        fBest = 0
        for f in xrange(layerIn.fSize):
          v = layerIn.get((xi,yi), f)
          if v > vmax:
            vmax = v
            fBest = f
            
        layerOutS2.arrayC1[xi][yi] = (vmax, fBest)
    
    return layerOutS2.arrayC1
  
  def getS2Cell(self, arrayC1, layerInput, pos):
    """
    Loop over each orientation in the input layer (C1) and create
    a composite of the best matches in the local neighborhood of the
    input position (pos).
    @param pos: (x,y) tuple position in the image to center the filter on.
    """
    cx,cy = pos
    size = self.xyCountMin
    
    #Get the boundary indicies for the part of the image to filter,
    #if any part of the filter spills over edge of image, cannot calculate
    (xi1,xi2), xOK = layerInput.getXRFNear(cx, size)
    if not xOK:
      return 0
    (yi1,yi2), yOK = layerInput.getYRFNear(cy, size)
    if not yOK:
      return 0
    
    #Return the subset of the C1 composite as an S2Cell
    return S2Cell(arrayC1[xi1:xi2+1,yi1:yi2+1])
  
  
  def learnPatch(self, layerInC1, arrayC1):
    """
    Randomly choose several sparsified patches from C1.
    A patch must have at least 25% non-zero values.
    If so, find its RBF dist from each of previously learned
    patches and only accept this new patch if it has an RBF
    dist greater than threshold.  This helps ensure a minimal
    amount of variation amongst the learned patches for S2.
    Stop and learn nothing from current layer if x number of
    attempted patches all fail the variation requirements.
    """
    #random.sample(range(10), 3) --> [3,8,1]
    #random.randint(min, max)
    if len(self.learned) >= 100:
      print "Max 100 patches learned."
      return
    
    #loop: while not added patch and < maxIter:
    for i in xrange(10):
      size = 4#random.randint(4,6)
      x = random.randint(0,layerInC1.xSize-size)
      y = random.randint(0,layerInC1.ySize-size)
      
      #patch must have >= x% non-zero values
      #layerOutS2.arrayC1[xi][yi] = (vmax, fBest)
      vPatch = arrayC1[x:x+size,y:y+size,0]
      minNonZeros = round(size*size * GRBFFilter.MIN_NONZERO_PCT)
      if len(numpy.flatnonzero(vPatch)) < minNonZeros:
        continue
      
      #patch must be >= thresholdDist from all learned
      uniquePatch = True
      for f in xrange(len(self.learned)):
        if size!=len(self.learned[f]): #must be same size to compare
          continue
        
        d = self.calculateRBF(layerInC1, (x,y), size, f)
        if d > GRBFFilter.SPATIAL_POOL_DIST:
          #print "S2 Fail d = ",d,f,(x,y,size)
          uniquePatch = False
          break
        #else:
        #  print "S2 OK d = ",d,f
      if not uniquePatch:
        continue
    
      #get sparsified patch from C1
      patch = arrayC1[x:x+size,y:y+size]
      self.learned.append(patch)
      self.lastLearned = (x,y,size)
      print "S2 Patches Learned: ",len(self.learned), self.lastLearned, i
      return
    
    print "No learned patch."
  
  def computeUnit(self, layerInputs, pos, f):
    """
    @param pos: (x,y) tuple position in the image to center the filter on.
    @param f: feature index of learned feature to test input against.
    """
    cx,cy = pos
    size = len(self.learned[f])
    layerInput = layerInputs[0]
    
#    s4x4, sumv = self.getS2Unit(layerInput, pos)
#    if f==0:
#      return s4x4
    
    #Weighted summary: sum(4x4)
    
    #Learning S2:
    #  each S2 cell contains a 4x4 of (vmax,f) values.
    #  calculate weighted summary of each 4x4
    #    hold on to top X (3/4?) weighted S2 cells
    #    store each 4x4 with relative positions to each other
    #    learned[i] = (4x4, 4x4, 4x4), (pos, pos, pos)
    #       pos is relative to center of all 3
    #
    #Inference S2:
    #  find top X current S2 cells
    #    compare S2-cell network to each stored network
    #    if max match is above some threshold, image is matched
    
    #Get the boundary indicies for the part of the image to filter,
    #if any part of the filter spills over edge of image, cannot calculate
    (xi1,xi2), xOK = layerInput.getXRFNear(cx, size)
    if not xOK:
      return 0
    (yi1,yi2), yOK = layerInput.getYRFNear(cy, size)
    if not yOK:
      return 0
    
    #Now apply template F to the receptive field.
    lpos = (xi1,yi1)
    return self.calculateRBF(layerInput, lpos, size, f)
  
  def calculateRBF(self, layerIn, lpos, size, f):
    """ 
    Calculate the Radial-Basis-Function distance between the learned
    template patch at index f to the patch from layerIn at layer position 
    lpos and of the specified patch size
    """
    #Now apply template F to the receptive field.
    xi1, yi1 = lpos
    res = 0.0
    for xi in xrange(xi1,xi1+size):
      for yi in xrange(yi1,yi1+size):
        w,pf = self.learned[f][xi-xi1][yi-yi1]
        v = layerIn.get((xi,yi), pf)
        diff = v-w
        res -= diff**2
    
    #RBF will return between 1.0 and 0.0 where 1 is perfect match and
    #0 is very far away; with gaussian curve in-between the 2
    xyRatio = size / self.xyCountMin
    return numpy.exp(res / (2.0 * self.sigma**2 - xyRatio**2))
  
  def getInputBoundBox(self, layer, rbbox):
    """
    @param layerInput: the layer the filter will read input values from.
    @param rbbox: the retinal bound box within the current layer.
    @return tuple (x,y, w,h) bounding box pixel coordinates.
    """
    size = self.xyCountMin#xyCounts[f]
    
    #Get the boundary indicies for the part of the image to filter,
    #if any part of the filter spills over edge of image, cannot calculate
    cx,cy = rbbox[0:2]
    (xi1,xi2), xOK = layer.getXRFNear(cx, size)
    (yi1,yi2), yOK = layer.getYRFNear(cy, size)
    xi, yi = min(xi1,xi2), min(yi1,yi2)
    
    cx,cy = rbbox[0]+rbbox[2], rbbox[1]+rbbox[3]
    (xi1,xi2), xOK = layer.getXRFNear(cx, size)
    (yi1,yi2), yOK = layer.getYRFNear(cy, size)
    xi2,yi2 = max(xi1,xi2), max(yi1,yi2)
    
    return (xi,yi, xi2-xi, yi2-yi)
    
        