"""
Created on Jan 5, 2011

@author: Barry Maturkanich

Code to represent an entire Hierarchical Temporal Memory (HTM) Region of 
Columns that implement Numenta's new Cortical Learning Algorithms (CLA).

The Region is defined by a matrix of columns, each of which contains several
cells.  The main idea is that given a matrix of input bits, the Region will
first sparsify the input such that only a few Columns will become 'active'.
As the input matrix changes over time, different sets of Columns will
become active in sequence.  The Cells inside the Columns will attempt
to learn these temporal transitions and eventually the Region will be
able to make predictions about what may happen next given what has happened
in the past.

For (much) more information, visit www.numenta.com.

SpatialPooling snippet from the Numenta docs:

The code computes activeColumns(t) = the list of columns that win due to 
the bottom-up input at time t. This list is then sent as input to the 
temporal pooler routine.

Phase 1: compute the overlap with the current input for each column
Phase 2: compute the winning columns after inhibition
Phase 3: update synapse permanence and internal variables

1) Start with an input consisting of a fixed number of bits. These bits might represent 
   sensory data or they might come from another region lower in the hierarchy.
2) Assign a fixed number of columns to the region receiving this input. Each column has 
   an associated dendrite segment. Each dendrite segment has a set of potential synapses 
   representing a subset of the input bits. Each potential synapse has a permanence value.
   Based on their permanence values, some of the potential synapses will be valid.
3) For any given input, determine how many valid synapses on each column are 
   connected to active input bits.
4) The number of active synapses is multiplied by a 'boosting' factor which is 
   dynamically determined by how often a column is active relative to its neighbors.
5) The columns with the highest activations after boosting disable all but a fixed 
   percentage of the columns within an inhibition radius. The inhibition radius is 
   itself dynamically determined by the spread (or 'fan-out') of input bits. There is 
   now a sparse set of active columns.
6) For each of the active columns, we adjust the permanence values of all the potential 
   synapses. The permanence values of synapses aligned with active input bits are 
   increased. The permanence values of synapses aligned with inactive input bits are 
   decreased. The changes made to permanence values may change some synapses from being 
   valid to not valid, and vice-versa.
"""

import random
import numpy
from math import exp, sqrt, ceil
from HTM.Column import Column
from HTM.Synapse import Synapse

RAD_BIAS_PEAK = 2 #input-bit radius bias peak for default proximal perms
RAD_BIAS_STD_DEV = 0.25 #input-bit radius standard deviation bias
DEBUG = True

class Region(object):
  """
  Represent an entire region of HTM columns for the CLA.
  """
  
  def __init__(self, inputSize, colGridSize, pctInputPerCol=0.05, pctMinOverlap=0.1, 
               localityRadius=0, pctLocalActivity=0.02, cellsPerCol=1, 
               segActiveThreshold=3, newSynapseCount=5):
    """
    Initialization (from Numenta docs):
    Prior to receiving any inputs, the region is initialized by computing a list of initial 
    potential synapses for each column. This consists of a random set of inputs selected 
    from the input space. Each input is represented by a synapse and assigned a random 
    permanence value. The random permanence values are chosen with two criteria. 
    First, the values are chosen to be in a small range around connectedPerm (the minimum 
    permanence value at which a synapse is considered "connected"). This enables potential 
    synapses to become connected (or disconnected) after a small number of training 
    iterations. Second, each column has a natural center over the input region, and the 
    permanence values have a bias towards this center (they have higher values near 
    the center).
    
    In addition to this I have added a concept of Locality Radius, which is an 
    additional parameter to control how far away synapse connections can be made
    instead of allowing connections anywhere.  The reason for this is that in the
    case of video images I wanted to experiment with forcing each Column to only
    learn on a small section of the total input to more effectively learn lines or
    corners in a small section without being 'distracted' by learning larger patterns
    in the overall input space (which hopefully higher hierarchical Regions would
    handle more successfully).  Passing in 0 for locality radius will mean no restriction
    which will more closely follow the Numenta doc if desired.
    
    @param inputSize: (x,y) size of input data matrix from the external source.
    @param colGridSize: (x,y) number of Columns to create to represent this Region.
    @param pctInputPerCol: Percent of input bits each Column has potential synapses for.
    @param pctMinOverlap: Minimum percent of column's synapses for column to be considered.
    @param localityRadius: Furthest number of columns away to allow distal synapses.
    @param pctLocalActivity: Approximate percent of Columns within locality radius to be 
    winners after inhibition.
    @param cellsPerCol: Number of (temporal context) cells to use for each Column.
    @param segActiveThreshold: Number of active synapses to activate a segment.
    @param newSynapseCount: number of new distal synapses added if none activated during 
    learning.
    """
    self.inputWidth = inputSize[0]#len(inputData)
    self.inputHeight = inputSize[1]#len(inputData[0])
    self.inputData = numpy.zeros(inputSize, dtype=numpy.uint8)
    
    self.localityRadius = localityRadius
    self.cellsPerCol = cellsPerCol
    self.segActiveThreshold = segActiveThreshold
    self.newSynapseCount = newSynapseCount
    
    self.pctInputPerCol = pctInputPerCol
    self.pctMinOverlap = pctMinOverlap
    self.pctLocalActivity = pctLocalActivity
    
    self.spatialLearning = False
    self.temporalLearning = False
    
    #Reduce the number of columns and map centers of input x,y correctly
    #For now: column grid will be half-lengths of input grid in both dimensions
    self.width = colGridSize[0]
    self.height = colGridSize[1]
    self.xSpace = (self.inputWidth-1*1.0) / (self.width-1)
    self.ySpace = (self.inputHeight-1*1.0) / (self.height-1)
    
    #Create the columns based on the size of the input data to connect to.
    self.columns = []
    self.columnGrid = []
    for cx in xrange(self.width):
      yCols = []
      for cy in xrange(self.height):
        srcPos = (int(cx*self.xSpace), int(cy*self.ySpace))
        col = Column(self, srcPos, (cx,cy))
        yCols.append(col)
        self.columns.append(col)
      self.columnGrid.append(yCols)
      
    self.outData = numpy.zeros((len(self.columnGrid), len(self.columnGrid[0])), dtype=numpy.uint8)
    
    #segmentUpdateList A list of segmentUpdate structures. segmentUpdateList(c,i)
    #   is the list of changes for cell i in column c.
    self.segmentUpdateMap = {}
    self.recentUpdateMap = {} #hold segments updated most recent time step
    
    #how far apart are 2 Columns in terms of input space; calc radius from that
    inputRadius = self.localityRadius*self.xSpace
    
    #Now connect all potentialSynapses for the Columns
    if self.localityRadius==0:
      synapsesPerSegment = int((self.inputWidth*self.inputHeight) * pctInputPerCol)
    else:
      synapsesPerSegment = int((inputRadius**2) * pctInputPerCol)
    
    #The minimum number of inputs that must be active for a column to be 
    #  considered during the inhibition step.
    self.minOverlap = synapsesPerSegment * pctMinOverlap
    
    longerSide = max(self.inputWidth, self.inputHeight)
    random.seed(42) #same connections each time for easier debugging
    
    inputRadius = int(round(inputRadius))
    minY = 0
    maxY = self.inputHeight-1
    minX = 0
    maxX = self.inputWidth-1
    for col in self.columns:
      #restrict synapse connections if localityRadius is non-zero
      if self.localityRadius > 0:
        minY = max(0, col.iy-inputRadius)
        maxY = min(self.inputHeight-1, col.iy+inputRadius)
        minX = max(0, col.ix-inputRadius)
        maxX = min(self.inputWidth-1, col.ix+inputRadius)
      #ensure we sample unique input positions to connect synapses to
      allPos = []
      for y in xrange(minY,maxY+1):
        for x in xrange(minX,maxX+1):
          allPos.append((x,y))
      for rx,ry in random.sample(allPos, synapsesPerSegment):
        inputCell = InputCell(rx, ry, self.inputData)
        permanence = random.gauss(Synapse.CONNECTED_PERM, Synapse.PERMANENCE_INC*2)
        distance = sqrt((col.ix-rx)**2 + (col.iy-ry)**2)
        localityBias = (RAD_BIAS_PEAK/0.4)*exp((distance/(longerSide*RAD_BIAS_STD_DEV))**2/-2)
        syn = Synapse(inputCell, permanence*localityBias)
        col.proximalSegment.addSynapse(syn)
    
#    if self.localityRadius>0:
#      self.inhibitionRadius = self.localityRadius
#    else:
    self.inhibitionRadius = self.__averageReceptiveFieldSize()
    
    #desiredLocalActivity A parameter controlling the number of columns that will be 
    #  winners after the inhibition step.
    if self.localityRadius==0:
      self.desiredLocalActivity = self.inhibitionRadius * pctLocalActivity
    else:
      self.desiredLocalActivity = (self.localityRadius**2) * pctLocalActivity
    self.desiredLocalActivity = int(max(2, round(self.desiredLocalActivity))) #at least 1
    
    if DEBUG:
      print "\nRegion Created"
      print "columnGrid = ",self.outData.shape
      print "xSpace, ySpace = ",self.xSpace, self.ySpace
      print "inputRadius = ",inputRadius
      print "desiredLocalActivity = ", self.desiredLocalActivity
      print "synapsesPerProximalSegment = ", synapsesPerSegment
      print "minOverlap = ",self.minOverlap
      print "conPerm,permInc = ", Synapse.CONNECTED_PERM, Synapse.PERMANENCE_INC
  
  def runOnce(self):
    """
    Run one time step iteration for this Region.  All cells will have their current
    (last run) state pushed back to be their new previous state and their new current 
    state reset to no activity.  Then SpatialPooling following by TemporalPooling is 
    performed for one time step.
    """
    for col in self.columns:
      for cell in col.cells:
        cell.nextTimeStep()
    self.__performSpatialPooling()
    self.__performTemporalPooling()
  
  def updateInput(self, newInput):
    """ 
    Update the values of the inputData for this Region by copying row
    references from the specified newInput parameter.
    @param newInput: 2d numpy matrix to use for next Region time step.
    The newInput array must have the same shape as the original inputData.
    """
    assert newInput.shape==self.inputData.shape
    for i in xrange(len(self.inputData)):
      self.inputData[i] = newInput[i]
  
  def getOutput(self):
    """ 
    Determine the output bit-matrix of the most recently run time step
    for this Region.  The Region output is a 2d numpy array representing all
    Columns present in the Region.  Bits are set to 1 if a Column is active or
    it contains at least 1 predicting cell, all other bits are 0. The output data
    will be a 2d numpy array of dimensions corresponding the column grid
    for this Region.  (Note: the Numenta doc suggests the Region output
    should potentially include bits for each individual cell.  My first-pass 
    implementation is Column only for now since in the case or 2 or 3 cells, the
    spatial positioning of the original grid shape can become lost and I'm
    not sure yet how desirable this is or isn't for the case of video input).
    @return a 2d numpy array of same shape as the column grid containing the
    Region's collective output.
    """
    for col in self.columns:
      if col.isActive:
        self.outData[col.cx][col.cy] = 1
      else:
        self.outData[col.cx][col.cy] = 0
        for cell in col.cells:
          if cell.isPredicting:
            self.outData[col.cx][col.cy] = 1
            break
    return self.outData
  
  def __performSpatialPooling(self):
    """
    Perform SpatialPooling for the current input in this Region.
    The result will be a subset of Columns being set as active as well
    as (proximal) synapses in all Columns having updated permanences and 
    boosts, and the Region will update inhibitionRadius.
    
    From the Numenta Docs:
    Phase 1: compute the overlap with the current input for each column.
    Given an input vector, the first phase calculates the overlap of each 
    column with that vector. The overlap for each column is simply the number 
    of connected synapses with active inputs, multiplied by its boost. If 
    this value is below minOverlap, we set the overlap score to zero.
    
    Phase 2: compute the winning columns after inhibition.
    The second phase calculates which columns remain as winners after the 
    inhibition step. desiredLocalActivity is a parameter that controls the 
    number of columns that end up winning. For example, if desiredLocalActivity
    is 10, a column will be a winner if its overlap score is greater than the
    score of the 10'th highest column within its inhibition radius.
    
    Phase 3: update synapse permanence and internal variables.
    The third phase performs learning; it updates the permanence values of all 
    synapses as necessary, as well as the boost and inhibition radius.
    
    The main learning rule is implemented in lines 20-26. For winning columns, 
    if a synapse is active, its permanence value is incremented, otherwise it 
    is decremented. Permanence values are constrained to be between 0 and 1.
    
    Lines 28-36 implement boosting. There are two separate boosting mechanisms 
    in place to help a column learn connections. If a column does not win often 
    enough (as measured by activeDutyCycle), its overall boost value is 
    increased (line 30-32). Alternatively, if a column's connected synapses 
    do not overlap well with any inputs often enough (as measured by 
    overlapDutyCycle), its permanence values are boosted (line 34-36). 
    Note: once learning is turned off, boost(c) is frozen.
    Finally at the end of Phase 3 the inhibition radius is recomputed (line 38).
    """
    #Phase 1: Compute Column Input Overlaps
    for col in self.columns:
      col.computeOverlap()
    
    #Phase 2: Compute Active Columns (Winners after inhibition)
    for col in self.columns:
      col.isActive = False
      if col.overlap > 0:
        minLocalActivity = self.__kthScore(self.neighbors(col), self.desiredLocalActivity)
        if(col.overlap >= minLocalActivity):
          col.isActive = True
    
    #Phase 3: Synapse Boosting (Learning)
    if self.spatialLearning:
      for col in self.columns:
        if col.isActive:
          col.updatePermanences()
      
      for col in self.columns:
        col.performBoosting()
      
      self.inhibitionRadius = self.__averageReceptiveFieldSize()
  
  def neighbors(self, column):
    """
    Return the list of all the columns that are within inhibitionRadius of the input column.
    """
    irad = int(round(self.inhibitionRadius))
    x0 = max(0, min(column.cx-1, column.cx-irad))
    y0 = max(0, min(column.cy-1, column.cy-irad))
    x1 = min(self.width, max(column.cx+1, column.cx+irad))
    y1 = min(self.height, max(column.cy+1, column.cy+irad))
    #print "neighbors of col(",column.ix,column.iy,") = ",x0,y0,",",x1,y1
    x1 = min(len(self.columnGrid), x1+1) #extra 1 for correct looping
    y1 = min(len(self.columnGrid[0]), y1+1) #extra 1 for correct looping
    
    for x in xrange(x0, x1):
      for y in xrange(y0, y1):
        yield self.columnGrid[x][y]
  
  def __kthScore(self, cols, k):
    """ Given the list of columns, return the k'th highest overlap value. """
    sorted = []
    for c in cols:
      sorted.append(c.overlap)
    sorted.sort()
    i = max(0, min(len(sorted)-1, len(sorted)-k))
    return sorted[i]

  def __averageReceptiveFieldSize(self):
    """
    The radius of the average connected receptive field size of all the columns. 
    The connected receptive field size of a column includes only the connected 
    synapses (those with permanence values >= connectedPerm). This is used to 
    determine the extent of lateral inhibition between columns.
    @return the average connected receptive field size (in column grid space).
    """
    dists = [] 
    for col in self.columns: 
      for syn in col.getConnectedSynapses():
        d = ((col.ix-syn.inputSource.ix)**2 + (col.iy-syn.inputSource.iy)**2)**0.5
        dists.append(d / self.xSpace)
    return sum(dists) / len(dists)
  
  
  def __performTemporalPooling(self):
    """
    From the Numenta Docs:
    The input to this code is activeColumns(t), as computed by the spatial pooler. 
    The code computes the active and predictive state for each cell at the 
    current timestep, t. The boolean OR of the active and predictive states 
    for each cell forms the output of the temporal pooler for the next level.
    
    Phase 1: compute the active state, activeState(t), for each cell.
    The first phase calculates the activeState for each cell that is in a winning column. 
    For those columns, the code further selects one cell per column as the 
    learning cell (learnState). The logic is as follows: if the bottom-up 
    input was predicted by any cell (i.e. its predictiveState output was 1 due 
    to a sequence segment), then those cells become active (lines 23-27). 
    If that segment became active from cells chosen with learnState on, this 
    cell is selected as the learning cell (lines 28-30). If the bottom-up input 
    was not predicted, then all cells in the col become active (lines 32-34). 
    In addition, the best matching cell is chosen as the learning cell (lines 36-41) 
    and a new segment is added to that cell.
    
    Phase 2: compute the predicted state, predictiveState(t), for each cell.
    The second phase calculates the predictive state for each cell. A cell will turn on 
    its predictive state output if one of its segments becomes active, i.e. if 
    enough of its lateral inputs are currently active due to feed-forward input. 
    In this case, the cell queues up the following changes: a) reinforcement of the 
    currently active segment (lines 47-48), and b) reinforcement of a segment that
    could have predicted this activation, i.e. a segment that has a (potentially weak)
    match to activity during the previous time step (lines 50-53).
    
    Phase 3: update synapses.
    The third and last phase actually carries out learning. In this phase segment 
    updates that have been queued up are actually implemented once we get feed-forward 
    input and the cell is chosen as a learning cell (lines 56-57). Otherwise, if the 
    cell ever stops predicting for any reason, we negatively reinforce the segments 
    (lines 58-60).
    """
    #Phase1
    #18. for c in activeColumns(t)
    #19.
    #20.   buPredicted = false
    #21.   lcChosen = false
    #22.   for i = 0 to cellsPerColumn - 1
    #23.     if predictiveState(c, i, t-1) == true then
    #24.       s = getActiveSegment(c, i, t-1, activeState)
    #25.       if s.sequenceSegment == true then
    #26.         buPredicted = true
    #27.         activeState(c, i, t) = 1
    #28.         if segmentActive(s, t-1, learnState) then
    #29.           lcChosen = true
    #30.           learnState(c, i, t) = 1
    #31.
    #32.   if buPredicted == false then
    #33.     for i = 0 to cellsPerColumn - 1
    #34.       activeState(c, i, t) = 1
    #35.
    #36.   if lcChosen == false then
    #37.     i,s = getBestMatchingCell(c, t-1)
    #38.     learnState(c, i, t) = 1
    #39.     sUpdate = getSegmentActiveSynapses (c, i, s, t-1, true)
    #40.     sUpdate.sequenceSegment = true
    #41.     segmentUpdateList.add(sUpdate)
    
    #Phase 1: Compute cell active states and segment learning updates
    for col in self.columns:
      if col.isActive:
        buPredicted = False
        learningCellChosen = False
        for cell in col.cells:
          if cell.wasPredicted:
            segment = cell.getPreviousActiveSegment()
            
            if segment and segment.isSequence:
              buPredicted = True
              cell.isActive = True
              
              if self.temporalLearning and segment.wasActiveFromLearning():
                learningCellChosen = True
                cell.isLearning = True
                #print "learning cell ",col.cx,col.cy
        
        if not buPredicted:
          for cell in col.cells:
            cell.isActive = True
            
        if self.temporalLearning and not learningCellChosen:
          bestCell, bestSeg = col.getBestMatchingCell(isSequence=True, previous=True)
          bestCell.isLearning = True
          
          segmentToUpdate = bestCell.getSegmentActiveSynapses(previous=True, \
                                                              segment=bestSeg, \
                                                              newSynapses=True)
          segmentToUpdate.isSequence = True
          segList = self.segmentUpdateMap.get(bestCell, [])
          segList.append(segmentToUpdate)
          self.segmentUpdateMap[bestCell] = segList
          
          #bestSeg may be partial-sort-of match, but it could dec-perm
          #other syns from different step if cell overlaps...
          
          #try better minOverlap to prevent bad boosting?
          #try to disable learning if predictions match heavily?
          
          #Do we need to enforce max segments per cell?
#          if not bestSeg:
#            print "New seqSegment on col ",col.ix,col.iy
#          else:
#            print "Update segSegment on cel ",col.ix,col.iy

          
    #Phase2
    #42. for c, i in cells
    #43.   for s in segments(c, i)
    #44.     if segmentActive(s, t, activeState) then
    #45.       predictiveState(c, i, t) = 1
    #46.
    #47.       activeUpdate = getSegmentActiveSynapses (c, i, s, t, false)
    #48.       segmentUpdateList.add(activeUpdate)
    #49.
    #50.       predSegment = getBestMatchingSegment(c, i, t-1)
    #51.       predUpdate = getSegmentActiveSynapses(
    #52.                                   c, i, predSegment, t-1, true)
    #53.       segmentUpdateList.add(predUpdate)
    for col in self.columns:
      for cell in col.cells:
        activeSegs = set({})
        for seg in cell.segments:
          if seg.isActive():
            cell.isPredicting = True
            activeSegs.add(seg)
            
            #a) reinforcement of the currently active segment, and 
            if self.temporalLearning:
              activeSegUpdate = cell.getSegmentActiveSynapses(segment=seg)
              segList = self.segmentUpdateMap.get(cell, [])
              segList.append(activeSegUpdate)
              self.segmentUpdateMap[cell] = segList
            break
        
        #b) reinforcement of a segment that could have predicted 
        #   this activation, i.e. a segment that has a (potentially weak)
        #   match to activity during the previous time step (lines 50-53).
        if self.temporalLearning and cell.isPredicting:
          predSegment = cell.getBestMatchingSegment(isSequence=False, previous=True)
#          if predSegment:
#            if not predSegment:
#              print "New predSegment on col ",col.irow,col.icol
#            elif predSegment not in activeSegs:
#              print "predSegment update 2x on col",col.irow,col.icol
          #TODO if predSegment is None, do we still add new? ok if same as above seg?
          predSegUpdate = cell.getSegmentActiveSynapses(previous=True, \
                                                        segment=predSegment, \
                                                        newSynapses=True)
          segList = self.segmentUpdateMap.get(cell, [])
          segList.append(predSegUpdate)
          self.segmentUpdateMap[cell] = segList
    
    #Phase3
    #54. for c, i in cells
    #55.   if learnState(c, i, t) == 1 then
    #56.     adaptSegments (segmentUpdateList(c, i), true)
    #57.     segmentUpdateList(c, i).delete()
    #58.   else if predictiveState(c, i, t) == 0 and predictiveState(c, i, t-1)==1 then
    #59.     adaptSegments (segmentUpdateList(c,i), false)
    #60.     segmentUpdateList(c, i).delete()
    self.recentUpdateMap.clear()
    if not self.temporalLearning:
      return
    for col in self.columns:
      for cell in col.cells:
        if cell not in self.segmentUpdateMap:
          continue
        if cell.isLearning:
          #print "cell from (",col.ix,col.iy,") adapted positive"
          self.adaptSegments(self.segmentUpdateMap[cell], positiveReinforcement=True)
          self.recentUpdateMap[cell] = self.segmentUpdateMap.pop(cell)
        elif not cell.isPredicting and cell.wasPredicted:
          #print "cell from (",col.ix,col.iy,") adapted negative"
          self.adaptSegments(self.segmentUpdateMap[cell], positiveReinforcement=False)
          self.recentUpdateMap[cell] = self.segmentUpdateMap.pop(cell)
  
  
  def adaptSegments(self, segmentUpdateList, positiveReinforcement):
    """
    This function iterates through a list of segmentUpdateInfo's and reinforces 
    each segment. For each segmentUpdate element, the following changes are 
    performed. If positiveReinforcement is true then synapses on the active 
    list get their permanence counts incremented by permanenceInc. All other 
    synapses get their permanence counts decremented by permanenceDec. If 
    positiveReinforcement is false, then synapses on the active list get 
    their permanence counts decremented by permanenceDec. After this step, 
    any synapses in segmentUpdate that do yet exist get added with a permanence 
    count of initialPerm. These new synapses are randomly chosen from the 
    set of all cells that have learnState output = 1 at time step t.
    """
    for segInfo in segmentUpdateList:
      if segInfo.segment:
        if positiveReinforcement:
          for syn in segInfo.segment.synapses:
            if syn in segInfo.activeSynapses:
              syn.increasePermanence()
            else:
              syn.decreasePermanence()
        else:
          for syn in segInfo.activeSynapses:
            syn.decreasePermanence()
      
      #add new synapses (and new segment if necessary)
      segment = segInfo.segment
      if segInfo.addNewSynapses and positiveReinforcement:
        if not segInfo.segment:
          if len(segInfo.learningCells) > 0: #only add if learning cells available
            segment = segInfo.cell.createSegment(segInfo.learningCells)
            segInfo.addedSynapses = segment.synapses
            segment.isSequence = segInfo.isSequence
        elif len(segInfo.learningCells) > 0:
          #add new synapses to existing segment
          added = segInfo.segment.createSynapsesToLearningCells(segInfo.learningCells)
          segInfo.addedSynapses = added
  


class InputCell(object):
  """
  Represent a single input bit from an external source.
  """
  
  def __init__(self, ix, iy, inputData):
    self.ix = ix
    self.iy = iy
    self.inputData = inputData
    
  @property
  def isActive(self):
    return self.inputData[self.ix][self.iy]
