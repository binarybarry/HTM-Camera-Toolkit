'''
Created on Jan 20, 2011

@author: Barry Maturkanich
'''

import random
from HTM.Segment import Segment

MIN_SYNAPSES_PER_SEGMENT_THRESHOLD = 1

class Cell(object):
  """
  Represents an HTM sequence cell that belongs to a given Column.
  """
  
  def __init__(self, column, index):
    """ 
    Create a new Cell belonging to the specified Column. The index is an 
    integer id to distinguish this Cell from others in the Column. 
    """
    self.column = column
    self.index = index
    self.isActive = False
    self.__wasActive = False
    self.isPredicting = False
    self.__wasPredicted = False
    self.isLearning = False
    self.__wasLearning = False
    self.segments = []
  
  @property
  def wasActive(self):
    return self.__wasActive
  
  @property
  def wasLearning(self):
    return self.__wasLearning
  
  @property
  def wasPredicted(self):
    return self.__wasPredicted
  
  def nextTimeStep(self):
    """ 
    Advance this cell to the next time step. The current state of this cell
    (active, learning, predicting) will be set as the previous state and the current
    state will be reset to no cell activity by default until it can be determined. 
    """
    self.__wasPredicted = self.isPredicting
    self.__wasActive = self.isActive
    self.__wasLearning = self.isLearning
    self.isPredicting = False
    self.isActive = False
    self.isLearning = False
  
  def createSegment(self, learningCells):
    """
    Create a new segment for this Cell. The new segment will initially connect to
    at most newSynapseCount synapses randomly selected from the set of cells that
    were in the learning state at t-1 (specified by the learningCells parameter).
    @param learningCells: the set of available learning cells to add to the segment.
    @return the segment that was just created.
    """
    newSegment = Segment(self.column.region.segActiveThreshold)
    newSegment.createSynapsesToLearningCells(learningCells)
    self.segments.append(newSegment)
    return newSegment
    
  def getPreviousActiveSegment(self):
    """
    For this cell, return a segment that was active in the previous time
    step. If multiple segments were active, sequence segments are given preference. 
    Otherwise, segments with most activity are given preference.
    """
    activeSegs = [seg for seg in self.segments if seg.wasActive()]
    if len(activeSegs) == 1: #if only 1 active segment, return it
      return activeSegs[0]
    
    if len(activeSegs) > 1:
      #if >1 active segments, sequence segments given priority
      sequenceSegs = [seg for seg in activeSegs if seg.isSequence]
      if len(sequenceSegs) == 1:
        return sequenceSegs[0]
      elif len(sequenceSegs) > 1:
        activeSegs = sequenceSegs
      
      #if multiple possible segments, return segment with most activity
      bestSegment = activeSegs[0]
      mostActiveSyns = len(activeSegs[0].getPrevActiveSynapses())
      for seg in activeSegs[1:]:
        activeSyns = len(seg.getPrevActiveSynapses())
        if activeSyns > mostActiveSyns:
          mostActiveSyns = activeSyns
          bestSegment = seg
      return bestSegment
    
    return None
  
  def getSegmentActiveSynapses(self, previous=False, segment=None, newSynapses=False):
    """
    Return a SegmentUpdateInfo object containing proposed changes to the specified
    segment.  If the segment is None, then a new segment is to be added, otherwise
    the specified segment is updated.  If the segment exists, find all active
    synapses for the segment (either at t or t-1 based on the 'previous' parameter)
    and mark them as needing to be updated.  If newSynapses is true, then
    Region.newSynapseCount - len(activeSynapses) new synapses are added to the
    segment to be updated.  The (new) synapses are randomly chosen from the set
    of current learning cells (within Region.localityRadius if set).
    """
    #Return a list of proposed changes (synapses to update or add)
    #  to this segment.
    #activeSynapses are those that are active (at time t) (to inc or dec later).
    #If newSynapses, then add new synapses to the segment randomly
    #  sampled from set of cells with learn state True (at time t)
    #  Either:
    #    a) new segment and new synapses for it
    #    b) existing segment, only update perm of existing syns
    #    c) existing segment, update perm of existing syns and add new syns
    activeSyns = []
    if segment:
      if previous:
        activeSyns = segment.getPrevActiveSynapses()
      else:
        activeSyns = segment.getActiveSynapses()
    return SegmentUpdateInfo(self, segment, activeSyns, newSynapses)
  
  def getBestMatchingSegment(self, isSequence, previous=False):
    """
    For this cell (at t-1 if previous=True else at t), find the segment (only
    consider sequence segments if isSequence is True, otherwise only consider
    non-sequence segments) with the largest number of active synapses. 
    This routine is aggressive in finding the best match. The permanence 
    value of synapses is allowed to be below connectedPerm. 
    The number of active synapses is allowed to be below activationThreshold, 
    but must be above minThreshold. The routine returns that segment. 
    If no segments are found, then None is returned.
    """
    bestSegment = None
    bestSynapseCount = MIN_SYNAPSES_PER_SEGMENT_THRESHOLD
    segments = [seg for seg in self.segments if seg.isSequence==isSequence]
    for seg in segments:
      if previous:
        synCount = len(seg.getPrevActiveSynapses(connectedOnly=False))
      else:
        synCount = len(seg.getActiveSynapses(connectedOnly=False))
      if synCount > bestSynapseCount:
        bestSynapseCount = synCount
        bestSegment = seg
    
    return bestSegment
  

class SegmentUpdateInfo(object):
  """
  This data structure holds three pieces of information required to update 
  a given segment: 
  a) segment reference (None if it's a new segment), 
  b) a list of existing active synapses, and 
  c) a flag indicating whether this segment should be marked as a sequence
     segment (defaults to false).
  The structure also determines which learning cells (at this time step)
  are available to connect (add synapses to) should the segment get updated.
  If there is a locality radius set on the Region, the pool of learning cells
  is restricted to those with the radius.
  """
  
  def __init__(self, cell, segment, activeSynapses, addNewSynapses=False):
    self.cell = cell
    self.segment = segment
    self.activeSynapses = activeSynapses
    self.addNewSynapses = addNewSynapses
    self.isSequence = False
    self.addedSynapses = [] #once synapses added, store here to visualize later
    
    learningCells = set({}) #capture learning cells at this time step
    
    #do not add >1 synapse to the same cell on a given segment
    region = self.cell.column.region
    if addNewSynapses:
      segCells = set({})
      if self.segment:
        for syn in self.segment.synapses:
          segCells.add(syn.inputSource)
      #only allow connecting to Columns within locality radius
      cellCol = cell.column
      
      #if localityRadius is 0, it means 'no restriction'
      if region.localityRadius > 0:
        minY = max(0, cellCol.cy-region.localityRadius)
        maxY = min(region.height-1, cellCol.cy+region.localityRadius)
        minX = max(0, cellCol.cx-region.localityRadius)
        maxX = min(region.width-1, cellCol.cx+region.localityRadius)
      else:
        minY = 0
        maxY = region.height-1
        minX = 0
        maxX = region.width-1
        
      for y in xrange(minY,maxY+1):
        for x in xrange(minX,maxX+1):
          col = region.columnGrid[x][y]
          for cell in col.cells:
            if cell.wasLearning and cell not in segCells:
              learningCells.add(cell)
    
    synCount = region.newSynapseCount
    if self.segment:
      synCount = max(0, synCount-len(self.activeSynapses))
    synCount = min(len(learningCells), synCount) #clamp at # of learn cells
    
    self.learningCells = []
    if len(learningCells) > 0 and synCount > 0:
      self.learningCells = random.sample(learningCells, synCount)

