/*
 * Column.h
 *
 *  Created on: Sep 22, 2011
 *      Author: barry
 *
 * Represents a single column of cells within an HTM Region.
 */

#ifndef COLUMN_H_
#define COLUMN_H_

#include "Cell.h"

class Column {
public:
  Column() {}
  ~Column();
  void init(Region* region, int srcPosX, int srcPosY, int posX, int posY);

  void nextTimeStep();

  inline void setActive(bool isActive) { _isActive = isActive; }
  float getOverlapPercentage();
  void getConnectedSynapses(std::vector<Synapse*>& syns);
  Cell* getBestMatchingCell(Segment** &bestSeg, bool isSequence, bool previous=false);

  void computeOverlap();
  void updatePermanences();
  void performBoosting();

  float maxDutyCycle(std::vector<Column*>& cols);
  void increasePermanences(float scale);
  void updateActiveDutyCycle();
  void updateOverlapDutyCycle();
  float boostFunction(float minDutyCycle);

  inline int ix() { return _ix; }
  inline int iy() { return _iy; }
  inline int cx() { return _cx; }
  inline int cy() { return _cy; }
  inline bool isActive() { return _isActive; }
  inline int getOverlap() { return _overlap; }
  inline int numCells() { return _numCells; }
  inline Cell* getCell(int i) { return &_cells[i]; }
  inline Region* getRegion() { return _region; }

private:
  Region* _region; //parent region
  Cell* _cells;    //Sequence cells
  int _numCells;
  bool _isActive;  //whether or not this Column is currently active.

  //The list of potential synapses and their permanence values.
  Segment* _proximalSegment;

  //The boost value for column c as computed during learning.
  //used to increase the overlap value for inactive columns.
  float _boost;

  //A sliding average representing how often column c has been active
  //after inhibition (e.g. over the last 1000 iterations).
  float _activeDutyCycle;

  //A sliding average representing how often column c has had
  //significant overlap (i.e. greater than minOverlap) with its inputs
  //(e.g. over the last 1000 iterations).
  float _overlapDutyCycle;

  int _overlap; //the last computed input overlap for the Column.
  int _ix,_iy;  //'input' row and col
  int _cx,_cy;  //'column grid' row and col
};

#endif /* COLUMN_H_ */


/*
 *
 * EMA_ALPHA = 0.005     #Exponential Moving Average alpha value

class Column(object):
  """
  Represents a single column of cells within an HTM Region.
  """

  def setActive(self, isActive):
    """
    Toggle whether or not this Column is currently active.
    """
    self.isActive = isActive

  def getOverlapPercentage(self):
    """ Return the (last computed) input overlap for this Column in terms of the
    percentage of active synapses out of total existing synapses.  """
    return float(self.overlap) / float(max(1,len(self.proximalSegment.synapses)))

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
 */
