'''
Created on Jan 16, 2011

@author: Barry Maturkanich
'''

from HTM.Cell import Cell
from HTM.Segment import Segment
from HTM.Synapse import Synapse

EMA_ALPHA = 0.005     #Exponential Moving Average alpha value

class Column(object):
  """ 
  Represents a single column of cells within an HTM Region. 
  """
  
  def __init__(self, region, srcPos, pos):
    """ 
    Construct a new Column for the given parent region at source row/column
    position srcPos and column grid position pos.
    @param region the parent Region this Column belongs to.
    @param srcPos a tuple (srcX,srcY) of this Column's 'center' position
                 in terms of the proximal-synapse input space.
    @param pos a tuple(x,y) of this Column's position within the
               Region's column grid.
    """
    self.region = region  #parent region
    self.cells = [Cell(self, i) for i in xrange(region.cellsPerCol)] #Sequence cells
    self.isActive = False #whether or not this Column is currently active.
    #The list of potential synapses and their permanence values.
    self.proximalSegment = Segment(region.segActiveThreshold)
    #The boost value for column c as computed during learning. 
    #  used to increase the overlap value for inactive columns.
    self.boost = 1.0
    #A sliding average representing how often column c has been active 
    #  after inhibition (e.g. over the last 1000 iterations).
    self.activeDutyCycle = 1.0
    #A sliding average representing how often column c has had 
    #  significant overlap (i.e. greater than minOverlap) with its inputs 
    #  (e.g. over the last 1000 iterations).
    self.overlapDutyCycle = 1.0
    self.overlap = 0 #the last computed input overlap for the Column.
    self.ix = srcPos[0] #'input' row and col
    self.iy = srcPos[1]
    self.cx = pos[0] #'column grid' row and col
    self.cy = pos[1]
  
  def setActive(self, isActive):
    """
    Toggle whether or not this Column is currently active.
    """
    self.isActive = isActive
  
  def getOverlapPercentage(self):
    """ Return the (last computed) input overlap for this Column in terms of the 
    percentage of active synapses out of total existing synapses.  """
    return float(self.overlap) / float(len(self.proximalSegment.synapses))
  
  def getConnectedSynapses(self):
    """ Return the list of all currently connected proximal synapses for 
    this Column. """
    return self.proximalSegment.getConnectedSynapses()
  
  def getBestMatchingCell(self, isSequence, previous=False):
    """
    For this column, return the cell with the best matching segment (at time t-1 if
    prevous=True else at time t). Only consider sequence segments if isSequence 
    is True, otherwise only consider non-sequence segments. If no cell has a 
    matching segment, then return the cell with the fewest number of segments.
    @return a list containing the best cell and its best segment (may be None).
    """
    bestCell = None
    bestSeg = None
    bestCount = 0
    for cell in self.cells:
      seg = cell.getBestMatchingSegment(isSequence, previous)
      if seg:
        if previous:
          synCount = len(seg.getPrevActiveSynapses(connectedOnly=False))
        else:
          synCount = len(seg.getActiveSynapses(connectedOnly=False))
        if synCount > bestCount:
          bestCell = cell
          bestSeg = seg
          bestCount = synCount
    
    if not bestCell:
      bestCell = self.cells[0]
      fewestCount = len(bestCell.segments)
      for cell in self.cells[1:]:
        if len(cell.segments) < fewestCount:
          fewestCount = len(cell.segments)
          bestCell = cell
    
    return bestCell, bestSeg
  
  def computeOverlap(self):
    """ 
    The spatial pooler overlap of this column with a particular input pattern.
    The overlap for each column is simply the number of connected synapses with active 
    inputs, multiplied by its boost. If this value is below minOverlap, we set the 
    overlap score to zero.
    """
    overlap = len(self.proximalSegment.getActiveSynapses())
    
    if overlap < self.region.minOverlap:
      overlap = 0
    else:
      overlap *= self.boost
    self.overlap = overlap
  
  def updatePermanences(self):
    """
    Update the permanence value of every synapse in this column based on whether active.
    This is the main learning rule (for the column's proximal dentrite). 
    For winning columns, if a synapse is active, its permanence value is incremented, 
    otherwise it is decremented. Permanence values are constrained to be between 0 and 1.
    """
    for syn in self.proximalSegment.synapses:
      if syn.isActive():
        syn.increasePermanence()
      else:
        syn.decreasePermanence()
  
  def performBoosting(self):
    """
    There are two separate boosting mechanisms 
    in place to help a column learn connections. If a column does not win often 
    enough (as measured by activeDutyCycle), its overall boost value is 
    increased (line 30-32). Alternatively, if a column's connected synapses 
    do not overlap well with any inputs often enough (as measured by 
    overlapDutyCycle), its permanence values are boosted (line 34-36). 
    Note: once learning is turned off, boost(c) is frozen.
    """
    #minDutyCycle(c) A variable representing the minimum desired firing rate for a cell. 
    #  If a cell's firing rate falls below this value, it will be boosted. This value is 
    #  calculated as 1% of the maximum firing rate of its neighbors.
    minDutyCycle = 0.01 * self.maxDutyCycle(self.region.neighbors(self))
    self.updateActiveDuteCycle()
    self.boost = self.boostFunction(minDutyCycle)
    
    self.updateOverlapDutyCycle()
    if self.overlapDutyCycle < minDutyCycle:
      self.increasePermanences(0.1*Synapse.CONNECTED_PERM)
  
  def maxDutyCycle(self, cols):
    """
    Returns the maximum active duty cycle of the columns in the given list 
    of columns.
    """
    return max((col.activeDutyCycle for col in cols))

  def increasePermanences(self, scale):
    """
    Increase the permanence value of every synapse in this column by a scale factor.
    """
    for syn in self.proximalSegment.synapses:
      syn.increasePermanence(scale)
  
  def updateActiveDuteCycle(self):
    """ 
    Computes a moving average of how often this column has been active 
    after inhibition.
    """
    newCycle = (1.0 - EMA_ALPHA) * self.activeDutyCycle
    if self.isActive:
      newCycle += EMA_ALPHA
    self.activeDutyCycle = newCycle

  def updateOverlapDutyCycle(self):
    """
    Computes a moving average of how often this column has overlap greater 
    than minOverlap.
    Exponential moving average (EMA):
    St = a * Yt + (1-a)*St-1
    """
    newCycle = (1.0 - EMA_ALPHA) * self.overlapDutyCycle
    if self.overlap > self.region.minOverlap:
      newCycle += EMA_ALPHA
    self.overlapDutyCycle = newCycle

  def boostFunction(self, minDutyCycle):
    """ 
    Returns the boost value of this column. The boost value is a scalar >= 1. 
    If activeDutyCyle(c) is above minDutyCycle(c), the boost value is 1. 
    The boost increases linearly once the column's activeDutyCycle starts 
    falling below its minDutyCycle.
    """
    if self.activeDutyCycle > minDutyCycle:
      return 1.0
    elif self.activeDutyCycle == 0.0:
      return self.boost * 1.05 #if 0 activeDuty, fix at +5%
    return minDutyCycle / self.activeDutyCycle
  