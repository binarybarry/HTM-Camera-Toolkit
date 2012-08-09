/*
 * Column.c
 *
 * Represents a single column of cells within an HTM Region.
 *
 *  Created on: Jul 21, 2012
 *      Author: barry
 */

#include <math.h>
#include <stdlib.h>
#include <stdio.h>
#include "Region.h"

float EMA_ALPHA = 0.005; /*Exponential Moving Average alpha value*/

/**
 *  Initialize the given Column to use the parent region at source row/column
 *  position srcPos and column grid position pos.
 *  @param region the parent Region this Column belongs to.
 *  @param srcPos (srcX,srcY) of this Column's 'center' position
 *               in terms of the proximal-synapse input space.
 *  @param pos (x,y) of this Column's position within the
 *             Region's column grid.
 */
void initColumn(Column* col, Region* region, int srcPosX, int srcPosY,
    int posX, int posY) {
  col->region = region;
  col->numCells = region->cellsPerCol;
  col->cells = malloc(col->numCells * sizeof(Cell));
  int i;
  for(i=0; i<col->numCells; ++i)
    initCell(&col->cells[i], col, i);
  col->isActive = false; /*whether or not this Column is currently active.*/

  /*The list of potential synapses and their permanence values.*/
  col->proximalSegment = malloc(sizeof(Segment));
  initSegment(col->proximalSegment, region->segActiveThreshold);

  /*The boost value for column c as computed during learning.
  //used to increase the overlap value for inactive columns.*/
  col->boost = 1.0f;

  /*A sliding average representing how often column c has been active
  //after inhibition (e.g. over the last 1000 iterations).*/
  col->activeDutyCycle = 1.0f;

  /*/A sliding average representing how often column c has had
  //significant overlap (i.e. greater than minOverlap) with its inputs
  //(e.g. over the last 1000 iterations).*/
  col->overlapDutyCycle = 1.0f;

  col->overlap = 0; /*the last computed input overlap for the Column.*/
  col->ix = srcPosX; /*'input' row and col*/
  col->iy = srcPosY;
  col->cx = posX; /*'column grid' row and col*/
  col->cy = posY;
}

/**
 * Free the memory that has been allocated by fields within the Column
 * structure.  In this case, free the array of cells that were allocated.
 * This function does NOT free the Column itself.
 */
void deleteColumn(Column* col) {
  int i;
  for(i=0; i<col->numCells; ++i)
    deleteCell(&(col->cells[i]));
  free(col->cells);
  free(col->proximalSegment);
  col->cells = NULL;
  col->proximalSegment = NULL;
}

/**
 * Increment all cells in this column to the next time step.
 */
void nextColumnTimeStep(Column* col) {
  int i;
  for(i=0; i<col->numCells; ++i)
    nextCellTimeStep(&(col->cells[i]));
}

/**
 * Return the (last computed) input overlap for this Column in terms of the
 * percentage of active synapses out of total existing synapses.
 */
float getOverlapPercentage(Column* col) {
  int numSyns = col->proximalSegment->numSynapses;
  if(numSyns==0)
    numSyns = 1;
  return ((float)col->overlap) / (float)numSyns;
}

/**
 * For this column, return the cell with the best matching segment (at time
 * t-1 if prevous=true else at time t). only consider segments that are
 * predicting cell activation to occur in exactly numPredictionSteps many
 * time steps from now. If no cell has a matching segment, then return the
 * cell with the fewest number of segments.
 * @param numPredictionSteps only consider segments that are predicting
 *  cell activation to occur in exactly this many time steps from now.
 * @param previous if true only consider active segments from t-1 else
 *  consider active segments right now.
 * @return an object containing the best cell and its best segment.
 */
Cell* getBestMatchingCell(Column* col, Segment** bestSegPtr, int* segmentID,
    int numPredictionSteps, bool previous) {
  Cell* bestCell = NULL;
  Segment* bestSeg = NULL;
  int bestCount = 0;
  int i, bestSegID;
  for(i=0; i<col->numCells; ++i) {
    Cell* cell = &(col->cells[i]);
    Segment* seg =
        getBestMatchingSegment(cell, numPredictionSteps, previous, &bestSegID);
    if(seg!=NULL) {
      int synCount = 0;
      if(previous)
        synCount = seg->numPrevActiveAllSyns;
      else
        synCount = seg->numActiveAllSyns;

      if(synCount > bestCount) {
        bestCell = cell;
        bestSeg = seg;
        *segmentID = bestSegID;
        bestCount = synCount;
      }
    }
  }

  if(bestCell==NULL) {
    bestCell = &(col->cells[0]);
    int fewestCount = bestCell->numSegments;
    for(i=1; i<col->numCells; ++i) {
      if(col->cells[i].numSegments < fewestCount) {
        fewestCount = col->cells[i].numSegments;
        bestCell = &(col->cells[i]);
      }
    }
  }

  *bestSegPtr = bestSeg;
  return bestCell;
}

/**
 * The spatial pooler overlap of this column with a particular input pattern.
 * The overlap for each column is simply the number of connected synapses with active
 * inputs, multiplied by its boost. If this value is below minOverlap, we set the
 * overlap score to zero.
 */
void computeOverlap(Column* col) {
  int overlap = col->proximalSegment->numActiveConnectedSyns;
  if(overlap < col->region->minOverlap)
    overlap = 0;
  else
    overlap = (int)((float)overlap*col->boost);
  col->overlap = overlap;
}

/**
 * Update the permanence value of every synapse in this column based on whether active.
 * This is the main learning rule (for the column's proximal dentrite).
 * For winning columns, if a synapse is active, its permanence value is incremented,
 * otherwise it is decremented. Permanence values are constrained to be between 0 and 1.
 */
void updateColumnPermanences(Column* col) {
  adaptSegmentPermanences(col->proximalSegment);
}

/**
 * Increase the permanence value of every synapse in this column by a scale factor.
 */
void increasePermanences(Column* col, float scale) {
  /*TODO consider scale parameter?*/
  updateSegmentPermanences(col->proximalSegment, true);
}

/**
 * Computes a moving average of how often this column has been active
 * after inhibition.
 */
void updateActiveDutyCycle(Column* col) {
  float newCycle = (1.0 - EMA_ALPHA) * col->activeDutyCycle;
  if(col->isActive)
    newCycle += EMA_ALPHA;
  col->activeDutyCycle = newCycle;
}

/**
 * Computes a moving average of how often this column has overlap greater
 * than minOverlap.
 * Exponential moving average (EMA):
 * St = a * Yt + (1-a)*St-1
 */
void updateOverlapDutyCycle(Column* col) {
  float newCycle = (1.0 - EMA_ALPHA) * col->overlapDutyCycle;
  if(col->overlap > col->region->minOverlap)
    newCycle += EMA_ALPHA;
  col->overlapDutyCycle = newCycle;
}

/**
 *  Returns the boost value of this column. The boost value is a scalar >= 1.
 *  If activeDutyCyle(c) is above minDutyCycle(c), the boost value is 1.
 *  The boost increases linearly once the column's activeDutyCycle starts
 *  falling below its minDutyCycle.
 */
float boostFunction(Column* col, float minDutyCycle) {
  if(col->activeDutyCycle > minDutyCycle)
    return 1.0;
  else if(col->activeDutyCycle==0.0)
    return col->boost * 1.05; /*if 0 activeDuty, fix at +5%*/
  return minDutyCycle / col->activeDutyCycle;
}

/**
 * There are two separate boosting mechanisms
 * in place to help a column learn connections. If a column does not win often
 * enough (as measured by activeDutyCycle), its overall boost value is
 * increased (line 30-32). Alternatively, if a column's connected synapses
 * do not overlap well with any inputs often enough (as measured by
 * overlapDutyCycle), its permanence values are boosted (line 34-36).
 * Note: once learning is turned off, boost(c) is frozen.
 */
void performBoosting(Column* col) {
  /*std::vector<Column*> neighborCols;
  //_region->neighbors(neighborCols, this);*/
  Region* region = col->region;
  int irad = round(region->inhibitionRadius);
  int x0 = max(0, min(col->cx-1, col->cx-irad));
  int y0 = max(0, min(col->cy-1, col->cy-irad));
  int x1 = min(region->width, max(col->cx+1, col->cx+irad));
  int y1 = min(region->height, max(col->cy+1, col->cy+irad));

  x1 = min(region->width, x1+1); /*extra 1's for correct looping*/
  y1 = min(region->height, y1+1);

  /*minDutyCycle(c) A variable representing the minimum desired firing rate
  //for a cell. If a cell's firing rate falls below this value, it will be
  //boosted. This value is calculated as 1% of the maximum firing rate of
  //its neighbors.*/
  float maxDuty = 0.0;
  int x, y;
  for(x=x0; x<x1; ++x) {
    for(y=y0; y<y1; ++y) {
      Column* col = &(region->columns[(y*region->height)+x]);
      if(col->activeDutyCycle > maxDuty)
        maxDuty = col->activeDutyCycle;
    }
  }

  float minDutyCycle = 0.01 * maxDuty;/*maxDutyCycle(neighborCols);*/
  updateActiveDutyCycle(col);
  col->boost = boostFunction(col, minDutyCycle);

  updateOverlapDutyCycle(col);
  if(col->overlapDutyCycle < minDutyCycle)
    increasePermanences(col, 0.1*CONNECTED_PERM);
}

