"""
Created on May 5, 2011

@author: Barry Maturkanich

Implementation of the GRBFFilter (S2) used by the HMAX algorithm.
The GRBF stands for Gaussian Radial-Basis-Function.  

This filter has both a learning and inference phase.  In the learning phase
we are learning small (typically 4x4) patches of inputs from the C1 MaxFilter
layers and storing them as templates to compare against during inference.

When this filter reads input from C1 it will only use the maximum response 
across all orientations per position.  This can be thought of as viewing the
input as a "C1 Composite" where only the strongest orientation per location
are considered and the rest ignored.

In either phase we start by creating the C1 Composite.

In learning we then select a random 4x4 input patch from the composite and
we only store it as a learned template patch if:
1) At least 25% of the cells are non-zero and
2) The patch has less than x% similarity to any existing learned patch.
   Meaning if we have 10 learned patches already, and our similarly threshold
   is 90%, then we will not accept a new patch unless its RBF value is below 90%
   similar to all the existing patches.
   This helps ensure a minimal level of uniqueness/variety among learned 
   patch templates.
If a candidate patch fails, we will retry up to x (default 25) other patches
within the C1 Composite before giving up and assuming the layer is too similar.

Once we have enough template patches learned we can run the filter in inference.
For inference each patch in the current C1 Composite is compared against all
learned template patches and scored using a Gaussian Radial-Basis-Function
similarity value.  All of these values are sent as output to the next layer.

The GRBF response of a patch of C1 units X to a particular S2 template/patch P is:
R(X,P) = exp(-(||X-P||^2) / 2sg^2*a)

sg = sigma (set to 1.0 currently)
a = alpha normalizing factor if patch sizes can vary (1.0 currently)
"""

import random
import numpy
import hmaxc
from HMAX.LevelFilter import LevelFilter

class S2Cell(object):
  """ 
  Helper object to store a single cell in the S2 layer.  A
  cell in this case corresponds to a patch of cells from the 
  C1 Composite layer. 
  """
  
  def __init__(self, s4x4):
    """ Initialize the S2 Cell with a 4x4 patch of C1 cells. """
    self.s4x4 = s4x4 #numpy(4x4) of (vmax,f) of C1 inputs
    self.__sumv = numpy.sum(s4x4[:,0]) #sum(vmax) in s4x4
    self.rpos = (0,0) #(xi,yi) relative integer layer position
    
  @property
  def sumv(self):
    return self.__sumv
    


class GRBFFilter(LevelFilter):
  """
  Gaussian Radial-Basis-Function filter (S2).
  Constructs a Composite of the C1 layer input and either learns templates of
  patches of C1 Composite cells or compares patches to previously learned
  template patches.
  """
  MIN_NONZERO_PCT = 0.25 #minimum % of values that must be non-zero to learn patch
  SPATIAL_POOL_DIST = 0.8#learned patches must have RBF dist less than this
  MAX_PATCHES = 50 #maximum number of template patches to learn

  def __init__(self, xyCountMin=4, sigma=1.0):
    """
    @param xyCountMin: edge size of the smallest feature to be learned.
    @param sigma: Standard deviation of the gaussian applied to the distance 
    between the template and the input patch.
    """
    self.xyCountMin = xyCountMin
    self.sigma = sigma
    self.learned = [] #list of numpyArrays for learned patches
    self.lastLearned = None
    self.isLearning = False
    random.seed(420)
  
  def computeLayer(self, layerOut):
    """
    Override the computeLayer from LevelFilter in order to first construct
    the single C1 Composite input to store only the strongest 1 orientation 
    per position.  We then proceed to perform either learning of input patches
    or inference/comparison of input patches to our previously learned set.
    @param layer: the output HmaxLayer to store results in.
    """
    out = layerOut
    layerIn = out.inputLayers[0]
    
    arrayC1 = self.buildCompositeC1(layerIn, layerOut)
    
    if self.isLearning:
      self.learnPatch(layerIn, arrayC1)
    else:
      self.computeLayerData(layerOut)
    
    #Calculate the arrayS2 used for rendering the state of the layer
    for xi in xrange(out.xSize):
      xc = out.xCenter(xi)
      for yi in xrange(out.ySize):
        yc = out.yCenter(yi)
        s2cell = self.getS2Cell(arrayC1, layerIn, (xc,yc))
#        out.set((xi,yi), 0, s2cell.sumv)
        out.arrayS2[xi][yi] = s2cell
  
  def computeLayerData(self, layerOut):
    """ 
    Method used during the data inference phase to compare patches from
    all layer positions with each of the previously learned template
    patches.  Store the results in the output layer.
    @param layerOut: the output HmaxLayer to store results in.
    """
    out = layerOut
    for f in xrange(len(self.learned)):
      for xi in xrange(out.xSize):
        xc = out.xCenter(xi)
        for yi in xrange(out.ySize):
          yc = out.yCenter(yi)
          val = self.computeUnit(out.inputLayers, (xc,yc), f)
          out.set((xi,yi), f, val)
  
  def clearLearnedPatches(self):
    """ 
    Clear/forget all learned patches in order to start over
    with new learning.
    """
    self.learned = []
  
  def buildCompositeC1(self, layerIn, layerOutS2):
    """ 
    Build the composite C1 used as the real input to S2.
    We simply loop over all positions in the C1 input layer
    and only keep the strongest orientation response per cell.
    @param layerIn: input C1 layer.
    @param layerOutS2: output S2 layer.
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
    if len(self.learned) >= GRBFFilter.MAX_PATCHES:
      print "Max patches learned."
      return
    
    #loop: while not added patch and < maxIter:
    for i in xrange(25):
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
      patch = numpy.array(arrayC1[x:x+size,y:y+size])
      self.learned.append(patch)
      self.lastLearned = (x,y,size)
      #print "S2 Patches Learned: ",len(self.learned), self.lastLearned, i
      return
    
    self.lastLearned = None
    #print "No learned patch."
  
  def computeUnit(self, layerInputs, pos, f):
    """
    Run the Filter on the input data from the previous network layer
    at the specified position. The result value will be returned and is
    expected to then be stored in the current output network layer.
    @param layerInputs: list of layer inputs this filter will read from.
    @param pos: (x,y) tuple position in the image to center the filter on.
    @param f: feature index of learned feature to test input against.
    """
    cx,cy = pos
    size = len(self.learned[f])
    layerInput = layerInputs[0]
    
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
    Determine the pixel bounding box corresponding to the input retinal-space
    bounding box.  This method is primarily used to generate feedback used
    in the UI to render input sources for higher layer results.
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
    

class GRBFFilterC(GRBFFilter):
  """
  GRBFFilterC is a python wrapper for the C++ hmaxc.GRBFFilterC object.
  The C++ implementation runs the same algorithm but with much better
  performance.  Currently only the inference phase is run by the C++
  implementation.
  """
  
  def __init__(self, xyCount=4, sigma=1.0):
    """
    @param xyCountMin: edge size of the smallest feature to be learned.
    @param sigma: Standard deviation of the gaussian applied to the distance 
    between the template and the input patch.
    """
    GRBFFilter.__init__(self, xyCount, sigma)
    
    self.cLearnedW = None
    self.cLearnedPF = None
    self.cGRBFFilter = hmaxc.GRBFFilterC(xyCount, sigma)
  
  def clearLearnedPatches(self):
    """ 
    Clear/forget all learned patches in order to start over
    with new learning.
    """
    GRBFFilter.clearLearnedPatches(self)
    self.cLearnedW = None
    self.cLearnedPF = None
    
  def computeLayerData(self, layerOut):
    """
    Override computeLayer so we call into C++ code for fast performance.
    @param layerOut: the output HmaxLayer to store results in.
    """
    if len(self.learned)==0: #if untrained, do not compute
      return
    if self.cLearnedW==None:
      self.cLearnedW = hmaxc.floatCArray(len(self.learned)*16)
      self.cLearnedPF = hmaxc.floatCArray(len(self.learned)*16)
      for f in xrange(len(self.learned)):
        fi = f*16
        #self.learned is [f][4][4][2] array...need to copy correctly
        for xi in xrange(4):
          for yi in xrange(4):
            w,pf = self.learned[f][xi][yi]
            self.cLearnedW[fi+((yi*4)+xi)] = w
            self.cLearnedPF[fi+((yi*4)+xi)] = pf
    
    #print "C++ GRBF:"
    layerIn = layerOut.inputLayers[0]
    self.cGRBFFilter.computeLayer(self.cLearnedW, self.cLearnedPF, \
                                  len(self.learned)*16, layerIn.cLayer, layerOut.cLayer)
    layerOut.setLayerDataFromCArray(checkSame=True)



