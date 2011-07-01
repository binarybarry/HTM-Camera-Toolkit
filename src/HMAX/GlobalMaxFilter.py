'''
Created on May 5, 2011

@author: barry
'''

import numpy
from libsvm import svmutil
from HMAX.LevelFilter import LevelFilter

class GlobalMaxFilter(LevelFilter):
  """
  Performs a per-feature global maximum over position and scale in one 
  or more input layers.
  """

  def __init__(self, sCount, thetas):
    """
    @param sCount: number of scales over which to pool.
    """
    self.sCount = sCount
    self.thetas = thetas
    self.isLearning = False
    self.learned = [] #svm data vectors of learned features
    self.classes = [] #svm class labels of learned features
    self.accuracy = 0.0
    self.svmModel = None
  
  def computeLayer(self, layer):
    """
    @param layer: the output HmaxLayer to store results in.
    """
    LevelFilter.computeLayer(layer)
    
    #need to enable learning mode from UI (after S2 trained)
    #during training, need to pass in class labels
    
    vec = layer.array[:,0,0].tolist()
    
    if self.isLearning:
      if len(self.learned)>=100 and self.svmModel==None:
        #model = svm_train(y, x [, 'training_options'])
        self.svmModel = svmutil.svm_train(self.classes, self.learned)
        return
      self.classes.append(0)
      self.learned.append(vec)
    elif self.svmModel!=None:
      #p_labs, p_acc, p_vals = svm_predict(y, x, model [,'predicting_options'])
      pLabs, pAcc, pVals = svmutil.svm_predict([0], vec, self.svmModel)
      print "SVM Result: ", pLabs, pAcc, pVals
          
  def computeUnit(self, layerInputs, pos, f):
    """
    @param layerInputs: assume this is tuple of sCount inputLayers.
    @param pos: (x,y) tuple position in the image to center the filter on.
    @param f: feature index of learned feature to test input against.
    """
    res = 0
    for s in xrange(self.sCount):
      layerInput = layerInputs[s]
      for xi in xrange(layerInput.xSize):
        for yi in xrange(layerInput.ySize):
          v = layerInput.get((xi,yi), f)
          res = max(res, v)
    
    return res


#  def computeLayer(self, layerOut):
#    """
#    @param layer: the output HmaxLayer to store results in.
#    """
#    def unravel(layerIn, index):
#      return (index / layerIn.ySize), (index % layerIn.ySize)
#    
#    def isAdjacent(ipos, lpos):
#      """ Is ipos (x,y) within 1 spot of any of (x,y) in lpos list. """
#      x,y = ipos
#      for (lx,ly) in lpos:
#        if abs(lx-x)<=1 and abs(ly-y)<=1:
#          return True
#      return False
#    
#    def insertPos(ipos, lpos):
#      """ Insert ipos into the lpos list such that position sort is maintained. """
#      x,y = ipos
#      for i in xrange(len(lpos)):
#        lx,ly = lpos[i]
#        if y<ly or (y==ly and x<lx):
#          lpos.insert(i, ipos)
#          return
#      lpos.append(ipos) #loop failed it means it adds at the end
#    
#    def createCluster(lpos, arrayS2):
#      """ 
#      Create a C2 cluster of S2 cells with relative positions generated
#      from the absoluate positions in lpos list.
#      @param arrayS2: matrix of S2Cell objects from input LayerS2.
#      """
#      cluster = []
#      for x,y in lpos:
#        cell = arrayS2[x][y]
#        if len(cluster)==0:
#          x0,y0 = x,y
#          cell.rpos = (0,0)
#        else:
#          cell.rpos = (x-x0, y-y0)
#        cluster.append(cell)
#      return cluster
#    
#    layerIn = layerOut.inputLayers[0]
#    
#    #Find max sumv from layerIn (x3)
#    #  remove max and bordering cells from consideration
#    #  Find max of remaining cells and remove bordering again ...x3
#    #Sort order by upper-left-most first, lower-right-most last
#    #and store relative positions with (0,0) being first one
#    inData = numpy.array(layerIn.getLayerData()).ravel()
#    isort = inData.argsort()
#    lpos = [unravel(layerIn, isort[-1])]
#    for i in xrange(len(isort)-2,-1,-1):
#      if len(lpos)>=3:
#        break
#      ipos = unravel(layerIn, isort[i])
#      if not isAdjacent(ipos, lpos):
#        insertPos(ipos, lpos)
#    #lpos is ordered list of (xi,yi) positions of S2 cells
#    
#    #print "S2 Maxes: ",lpos
#    cluster = createCluster(lpos, layerIn.arrayS2)
#    #rp = [cell.rpos for cell in cluster]
#    #print "S2 rpos: ",rp
#    
#    self.bestCluster = None
#    self.lastCluster = cluster
#    self.lastClusterPos = lpos[0]
#    
#    #If learning, store this cluster
#    if self.isLearning:
#      self.learned.append(cluster)
#      print "C2 Learned ",len(self.learned)
#    else:
#      #If inference, compare this cluster to learned clusters:
#      #  compare average of all distances of each (vmax,f)
#      #  compare distance of relative position
#      #return closest overall distance to any of learned clusters
#      pcts = numpy.zeros(len(self.learned))
#      for i in xrange(len(self.learned)):
#        pcts[i] = self.compareClusters(cluster, self.learned[i])
#      
#      #print "meanMatch: %g%%" % (pcts.mean()*100.0)
#      self.accuracy = pcts.mean()*100.0