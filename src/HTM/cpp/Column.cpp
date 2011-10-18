/*
 * Column.cpp
 *
 *  Created on: Sep 22, 2011
 *      Author: barry
 *
 * Represents a single column of cells within an HTM Region.
 */

#include <vector>
#include "Region.h"

float EMA_ALPHA = 0.005; //Exponential Moving Average alpha value

/**
 *  Construct a new Column for the given parent region at source row/column
 *  position srcPos and column grid position pos.
 *  @param region the parent Region this Column belongs to.
 *  @param srcPos (srcX,srcY) of this Column's 'center' position
 *               in terms of the proximal-synapse input space.
 *  @param pos (x,y) of this Column's position within the
 *             Region's column grid.
 */
void Column::init(Region* region, int srcPosX, int srcPosY, int posX, int posY) {
  _region = region;
  _numCells = region->getCellsPerCol();
  _cells = new Cell[_numCells];
  for(int i=0; i<_numCells; ++i)
    _cells[i].init(this, i); //context cells
  _isActive = false; //whether or not this Column is currently active.

  //The list of potential synapses and their permanence values.
  _proximalSegment = new Segment(region->getSegActiveThreshold());

  //The boost value for column c as computed during learning.
  //used to increase the overlap value for inactive columns.
  _boost = 1.0;

  //A sliding average representing how often column c has been active
  //after inhibition (e.g. over the last 1000 iterations).
  _activeDutyCycle = 1.0;

  //A sliding average representing how often column c has had
  //significant overlap (i.e. greater than minOverlap) with its inputs
  //(e.g. over the last 1000 iterations).
  _overlapDutyCycle = 1.0;

  _overlap = 0; //the last computed input overlap for the Column.
  _ix = srcPosX; //'input' row and col
  _iy = srcPosY;
  _cx = posX; //'column grid' row and col
  _cy = posY;
}

Column::~Column() {
  delete[] _cells;
  delete _proximalSegment;
}

/**
 * Increment all cells in this column to the next time step.
 */
void Column::nextTimeStep() {
  for(int i=0; i<_numCells; ++i)
    _cells[i].nextTimeStep();
}

/**
 *  Return the (last computed) input overlap for this Column in terms of the
 *  percentage of active synapses out of total existing synapses.
 */
float Column::getOverlapPercentage() {
  int numSyns = _proximalSegment->numSynapses();
  if(numSyns==0)
    numSyns = 1;
  return float(_overlap) / float(numSyns);
}

/**
 *  Return the list of all currently connected proximal synapses for this Column.
 */
void Column::getConnectedSynapses(std::vector<Synapse*>& syns) {
  return _proximalSegment->getConnectedSynapses(syns);
}

/**
 *  For this column, return the cell with the best matching segment (at time t-1 if
 *  prevous=True else at time t). Only consider sequence segments if isSequence
 *  is True, otherwise only consider non-sequence segments. If no cell has a
 *  matching segment, then return the cell with the fewest number of segments.
 *  @return a list containing the best cell and its best segment (may be None).
 */
Cell* Column::getBestMatchingCell(Segment** &bestSegPtr, bool isSequence, bool previous) {
  Cell* bestCell = NULL;
  Segment* bestSeg = NULL;
  int bestCount = 0;
  for(int i=0; i<_numCells; ++i) {
    Segment* seg = _cells[i].getBestMatchingSegment(isSequence, previous);
    if(seg!=NULL) {
      int synCount = 0;
      if(previous)
        synCount = seg->getPrevActiveSynapseCount(false);
      else
        synCount = seg->getActiveSynapseCount(false);

      if(synCount > bestCount) {
        bestCell = &_cells[i];
        bestSeg = seg;
        bestCount = synCount;
      }
    }
  }

  if(bestCell==NULL) {
    bestCell = &_cells[0];
    int fewestCount = bestCell->numSegments();
    for(int i=1; i<_numCells; ++i) {
      if(_cells[i].numSegments() < fewestCount) {
        fewestCount = _cells[i].numSegments();
        bestCell = &_cells[i];
      }
    }
  }

  bestSegPtr = &bestSeg;
  return bestCell;
}

/**
 *  The spatial pooler overlap of this column with a particular input pattern.
 *  The overlap for each column is simply the number of connected synapses with active
 *  inputs, multiplied by its boost. If this value is below minOverlap, we set the
 *  overlap score to zero.
 */
void Column::computeOverlap() {
  int overlap = _proximalSegment->getActiveSynapseCount();

  if(overlap < _region->getMinOverlap())
    overlap = 0;
  else
    overlap = int((float)overlap*_boost);
  _overlap = overlap;
}

/**
 *  Update the permanence value of every synapse in this column based on whether active.
 *  This is the main learning rule (for the column's proximal dentrite).
 *  For winning columns, if a synapse is active, its permanence value is incremented,
 *  otherwise it is decremented. Permanence values are constrained to be between 0 and 1.
 */
void Column::updatePermanences() {
  _proximalSegment->adaptPermanences();
}

/**
 *  There are two separate boosting mechanisms
 *  in place to help a column learn connections. If a column does not win often
 *  enough (as measured by activeDutyCycle), its overall boost value is
 *  increased (line 30-32). Alternatively, if a column's connected synapses
 *  do not overlap well with any inputs often enough (as measured by
 *  overlapDutyCycle), its permanence values are boosted (line 34-36).
 *  Note: once learning is turned off, boost(c) is frozen.
 */
void Column::performBoosting() {
  std::vector<Column*> neighborCols;
  _region->neighbors(neighborCols, this);

  //minDutyCycle(c) A variable representing the minimum desired firing rate
  //for a cell. If a cell's firing rate falls below this value, it will be
  //boosted. This value is calculated as 1% of the maximum firing rate of
  //its neighbors.
  float minDutyCycle = 0.01 * maxDutyCycle(neighborCols);
  updateActiveDutyCycle();
  _boost = boostFunction(minDutyCycle);

  updateOverlapDutyCycle();
  if(_overlapDutyCycle < minDutyCycle)
    increasePermanences(0.1*CONNECTED_PERM);
}

/**
 *  Returns the maximum active duty cycle of the columns in the given list
 *  of columns.
 */
float Column::maxDutyCycle(std::vector<Column*>& cols) {
  float maxd = 0.0;
  for(unsigned int i=0; i<cols.size(); ++i) {
    if(cols[i]->_activeDutyCycle > maxd)
      maxd = cols[i]->_activeDutyCycle;
  }
  return maxd;
}

/**
 *  Increase the permanence value of every synapse in this column by a scale factor.
 */
void Column::increasePermanences(float scale) {
  _proximalSegment->updatePermanences(true);
}

/**
 *  Computes a moving average of how often this column has been active
 *  after inhibition.
 */
void Column::updateActiveDutyCycle() {
  float newCycle = (1.0 - EMA_ALPHA) * _activeDutyCycle;
  if(_isActive)
    newCycle += EMA_ALPHA;
  _activeDutyCycle = newCycle;
}

/**
 *  Computes a moving average of how often this column has overlap greater
 *  than minOverlap.
 *  Exponential moving average (EMA):
 *  St = a * Yt + (1-a)*St-1
 */
void Column::updateOverlapDutyCycle() {
  float newCycle = (1.0 - EMA_ALPHA) * _overlapDutyCycle;
  if(_overlap > _region->getMinOverlap())
    newCycle += EMA_ALPHA;
  _overlapDutyCycle = newCycle;
}

/**
 *  Returns the boost value of this column. The boost value is a scalar >= 1.
 *  If activeDutyCyle(c) is above minDutyCycle(c), the boost value is 1.
 *  The boost increases linearly once the column's activeDutyCycle starts
 *  falling below its minDutyCycle.
 */
float Column::boostFunction(float minDutyCycle) {
  if(_activeDutyCycle > minDutyCycle)
    return 1.0;
  else if(_activeDutyCycle==0.0)
    return _boost * 1.05; //if 0 activeDuty, fix at +5%
  return minDutyCycle / _activeDutyCycle;
}



