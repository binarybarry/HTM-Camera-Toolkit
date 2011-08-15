"""
Created on May 5, 2011

@author: barry

Implementation of the GlobalMaxFilter (C2) used by the HMAX algorithm.

This filter performs two steps:
1) Perform a per-feature global maximum over position and scale.
2) Train and infer using an SVM (Support Vector Machine) classifier.

For (1) we receive input from the S2 GRBF layer.  This contains each layer
cell's match to each of all learned S2 template patches.  So you could
visualize this as a set of how well each template matched each position.

The GlobalMaxFilter will loop over this information and determine, for
each template patch, the value of the strongest match anywhere in the
layer.  So i.e. patch #1 was compared against every layer position; some
positions it did not match very well (~0.1) others better (~0.5) but in
one particular location it matched with 0.7.  So the GlobalMaxFilter will
simply take the 0.7 for patch 1.

The result is a set of maximum match values for each of the S2 template patches.

This result array is then fed into an SVM classifier in either a learning or
inference phase.

In the learning phase the user is expected to provide a class label (integer)
that identifies the image.  We then store all the pairings of 
(class-id, resultArray) and use these to train the SVM.

Later during inference we take the same result-array this time without a class-id
and ask the SVM to determine which class-id does the result most closely match.
The SVM provides a set of probability values giving its best estimate (based on
the earlier training data) how likely it is the current result matches the
learned classes.

The code uses the 3rd party 'libsvm' for the Support Vector Machine.
It was developed by Chih-Chung Chang and Chih-Jen Lin and is available from:
http://www.csie.ntu.edu.tw/~cjlin/libsvm/
"""

import numpy
import HMAX
from libsvm import svmutil
from HMAX.LevelFilter import LevelFilter

class GlobalMaxFilter(LevelFilter):
  """
  Performs a per-feature global maximum over position and scale in one 
  or more input layers.  Will then use an SVM (Support Vector Machine)
  classifier to learn and infer results for the input data.
  """

  def __init__(self, sCount):
    """
    @param sCount: number of scales over which to pool.
    """
    self.sCount = sCount
    self.isLearning = False
    self.learningClass = 1
    self.learned = [] #svm data vectors of learned features
    self.classes = [] #svm class labels of learned features
    self.__classCounts = {}
    self.__classImages = {} #map of classID to example input image
    self.__svmModel = None
  
  @property
  def numClasses(self):
    """ Return the number of distinct SVM classes this filter has learned data for. """
    return len(self.__classCounts)
  
  def hasBuiltSVM(self):
    """ Return true if the filter has successfully trained an SVM Model. """
    return self.__svmModel!=None
  
  def resetLearning(self):
    """ Reset/clear all learning that has occurred in this filter. """
    self.__svmModel = None
    self.__classCounts = {}
    self.__classImages = {}
    self.learned = []
    self.classes = []
  
  def getCount(self, classID=None):
    """ 
    Return a count of the number of examples that have been learned for 
    the specified class index.  If None is passed in then the method returns
    the cumulative count across all classes.  The method may return 0 if no
    examples have been learned for the given index.
    @param classID: index of the class to get a learn count for (None for cumulative).
    """
    if classID==None and len(self.__classCounts)>0:
      return numpy.array(self.__classCounts.values()).sum()
    return self.__classCounts.get(classID, 0)
  
  def finishLearning(self):
    """ 
    Method should be called to indicate that SVM learning is finished.
    When this happens we take all the learned values and feed them into
    a new SVM Model to train it for later inference.
    """
    if self.__svmModel==None:
      #model = svm_train(y, x [, 'training_options'])
      if HMAX.DEBUG:
        print "creating svmModel..."
      self.__svmModel = svmutil.svm_train(self.classes, self.learned, "-q -b 1")
      if HMAX.DEBUG:
        print "svmModel successfully trained"
  
  def computeLayer(self, layer):
    """
    Override the computeLayer from LevelFilter in order to continue
    with processing the learning or inferring using our SVM model.
    If the SVM is trained and we are inferring, then the SVM inference
    results are stored in the layer (which is assumed to be a LayerC2).
    The layers are able to render themselves onto a wx canvas for 
    inspection.
    @param layer: the output HmaxLayer to store results in.
    """
    LevelFilter.computeLayer(self, layer)
    
    #need to enable learning mode from UI (after S2 trained)
    #during training, need to pass in class labels
    vec = layer.array[:,0,0].tolist() #contains vector of C2 maxes
    
    if self.isLearning and self.__svmModel==None:
      #add to count for how many of this class have been learned
      count = self.__classCounts.get(self.learningClass, 0)
      self.__classCounts[self.learningClass] = count+1
      
      #copy base input image to use as example when showing SVM result
      if count==0:
        layer.saveExampleImage(self.learningClass)
      
      self.classes.append(self.learningClass)
      self.learned.append(vec)
      #print "learned svm ",len(self.learned),self.learningClass
    elif self.__svmModel!=None:
      #p_labs, p_acc, p_vals = svm_predict(y, x, model [,'predicting_options'])
      pLabs, pAcc, pVals = svmutil.svm_predict([0], [vec], self.__svmModel, "-b 1")
      pVals = pVals[0]
      #sort ids in case SVM classIDs not consecutive
      ids = sorted(self.__classCounts.keys())
      layer.setAccuracyResult(sorted(zip(pVals, ids),reverse=True))
      if HMAX.DEBUG:
        print "SVM Result: ", pLabs, pAcc, pVals
          
  def computeUnit(self, layerInputs, pos, f):
    """
    Run the Filter on the input data from the previous network layer
    at the specified position. The result value will be returned and is
    expected to then be stored in the current output network layer.
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

