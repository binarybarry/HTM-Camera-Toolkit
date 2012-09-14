/*
 * Cell.c
 *
 * Represents an HTM sequence cell that belongs to a given Column.
 *
 *  Created on: Jul 21, 2012
 *      Author: barry
 */

#include <stdlib.h>
#include <stdio.h>
#include "Region.h"

int MIN_SYNAPSES_PER_SEGMENT_THRESHOLD = 1;

/**
 * Initialize the given standard Cell by defining its parent Column and
 * index position within that column.
 */
void initCell(Cell* cell, Column* column, int index) {
  cell->column = column;
  cell->index = index;
  cell->isActive = false;
  cell->wasActive = false;
  cell->isPredicting = false;
  cell->wasPredicted = false;
  cell->isLearning = false;
  cell->wasLearning = false;
  cell->predictionSteps = 0;

  cell->numSegments = 0;
  cell->allocatedSegments = 10;
  cell->segments = malloc(cell->allocatedSegments * sizeof(Segment));

  cell->numSegUpdates = 0;
  cell->allocatedSegUpdates = 5;
  cell->segmentUpdates = malloc(cell->allocatedSegUpdates * sizeof(SegmentUpdateInfo));

  cell->region = column->region;
  int cpc = cell->region->cellsPerCol;
  cell->id = (column->cx*cpc + index) +
             (column->cy*cpc*cell->region->width);
}

/**
 * Initialize the given Cell as an InputCell.  An input cell is one that is directly
 * connected to the input data used by the first Region in the hierarchy.
 * This type of cell does not use the isPredicting or isLearning states, nor does it
 * use segment updates.
 * @param index the array index within the input data of the region that this
 * input cell is 'connected' to.
 */
void initInputCell(Cell* cell, Region* region, int index) {
  cell->region = region;
  cell->column = NULL;
  cell->index = index;

  cell->isActive = false;
  cell->wasActive = false;
  cell->isPredicting = false;
  cell->wasPredicted = false;
  cell->isLearning = false;
  cell->wasLearning = false;
  cell->predictionSteps = 0;

  cell->numSegments = 0;
  cell->allocatedSegments = 0;
  cell->segments = NULL;

  cell->numSegUpdates = 0;
  cell->allocatedSegUpdates = 0;
  cell->segmentUpdates = NULL;

  cell->id = 0;
}

/**
 * Free the memory that has been allocated by fields within the Cell
 * structure.  In this case, free the array of segments and segmentUpdates
 * that were allocated.  This function does NOT free the Cell itself.
 */
void deleteCell(Cell* cell) {
  int i;
  for(i=0; i<cell->numSegments; ++i)
    deleteSegment(&(cell->segments[i]));
  free(cell->segments);
  cell->segments = NULL;
  cell->numSegments = 0;
  cell->allocatedSegments = 0;

  for(i=0; i<cell->numSegUpdates; ++i)
    deleteSegmentUpdateInfo(&(cell->segmentUpdates[i]));
  free(cell->segmentUpdates);
  cell->segmentUpdates = NULL;
  cell->numSegUpdates = 0;
  cell->allocatedSegUpdates = 0;
}

/**
 * Toggle whether this Cell is currenty in the predicting state or not.
 * If the Cell enters the predicting state it will also cache the value of
 * the prediction steps for the active segment causing this Cell to predict.
 * If there are more than 1 such segment, we cache the value of the least
 * number of time steps until an activation occurs.  The cache value will
 * only reset each time the Cell enters a new predicting state.
 * @param predicting true if the Cell is now predicting, false if it no
 * longer is.
 */
void setCellPredicting(Cell* cell, bool predicting) {
  cell->isPredicting = predicting;
  if(cell->isPredicting) {
    cell->predictionSteps = MAX_TIME_STEPS;
    int i;
    for(i=0; i<cell->numSegments; ++i) {
      Segment* seg = &(cell->segments[i]);
      if(seg->isActive && seg->predictionSteps < cell->predictionSteps)
        cell->predictionSteps = seg->predictionSteps;
    }
  }
}

/**
 * Return the number of segments in this cell that match the number of
 * predictionSteps. If pass in zero, return count of total segments regardless
 * of predictionSteps.
 */
int numCellSegments(Cell* cell, int predictionSteps) {
  int c=0, i;
  for(i=0; i<cell->numSegments; ++i) {
    Segment* seg = &(cell->segments[i]);
    if(seg->predictionSteps==predictionSteps || predictionSteps==0)
      c++;
  }
  return c;
}

/**
 * Advance this cell to the next time step. The current state of this cell
 * (active, learning, predicting) will be set as the previous state and the current
 * state will be reset to no cell activity by default until it can be determined.
 */
void nextCellTimeStep(Cell* cell) {
  cell->wasActive = cell->isActive;
  cell->wasPredicted = cell->isPredicting;
  cell->wasLearning = cell->isLearning;
  cell->isActive = false;
  cell->isPredicting = false;
  cell->isLearning = false;
  int i;
  for(i=0; i<cell->numSegments; ++i) {
    Segment* seg = &(cell->segments[i]);
    nextSegmentTimeStep(seg);
  }
}

/**
 *  Create a new segment for this Cell. The new segment will initially connect to
 *  at most newSynapseCount synapses randomly selected from the set of cells that
 *  were in the learning state at t-1 (specified by the learningCells parameter).
 *  @param learningCells: the set of available learning cells to add to the segment.
 *  @return the segment that was just created.
 */
Segment* createCellSegment(Cell* cell) {
  /*if segment array is full, need to increase capacity to add more*/
  if(cell->numSegments == cell->allocatedSegments) {
    int newAllocation = cell->allocatedSegments*2;
    cell->segments = realloc(cell->segments, newAllocation * sizeof(Segment));
    cell->allocatedSegments = newAllocation;
  }

  Segment* seg = &(cell->segments[cell->numSegments]);
  initSegment(seg, cell->column->region->segActiveThreshold);
  cell->numSegments += 1;

  return seg;
}

/**
 * For this cell, return a segment that was active in the previous time
 * step. If multiple segments were active, sequence segments are given preference.
 * Otherwise, segments with most activity are given preference.
 */
Segment* getPreviousActiveSegment(Cell* cell) {
  bool foundSequence = false;
  int mostSyns=0, i;

  Segment* bestSegment = NULL;
  for(i=0; i<cell->numSegments; ++i) {
    Segment* seg = &(cell->segments[i]);
    int activeSyns = seg->numPrevActiveConnectedSyns;
    if(activeSyns > seg->segActiveThreshold) {
      /*if segment is active, check for sequence segment and compare active synapses*/
      if(seg->isSequence) {
        foundSequence = true;
        if(activeSyns > mostSyns) {
          mostSyns = activeSyns;
          bestSegment = seg;
        }
      }
      else if(!foundSequence) {
        if(activeSyns > mostSyns) {
          mostSyns = activeSyns;
          bestSegment = seg;
        }
      }
    }
  }

  return bestSegment;
}

/**
 * Return a SegmentUpdateInfo object containing proposed changes to the specified
 * segment.  If the segment is None, then a new segment is to be added, otherwise
 * the specified segment is updated.  If the segment exists, find all active
 * synapses for the segment (either at t or t-1 based on the 'previous' parameter)
 * and mark them as needing to be updated.  If newSynapses is true, then
 * Region.newSynapseCount - len(activeSynapses) new synapses are added to the
 * segment to be updated.  The (new) synapses are randomly chosen from the set
 * of current learning cells (within Region.localityRadius if set).
 *
 * These segment updates are only applied when the applySegmentUpdates
 * method is later called on this Cell.
 */
SegmentUpdateInfo* updateSegmentActiveSynapses(Cell* cell, bool previous,
    int segmentID, bool newSynapses) {
  /*if segmentUpdate array is full, need to increase capacity to add more*/
  if(cell->numSegUpdates == cell->allocatedSegUpdates) {
    int newAllocation = cell->allocatedSegUpdates*2;
    cell->segmentUpdates =
        realloc(cell->segmentUpdates, newAllocation * sizeof(SegmentUpdateInfo));
    cell->allocatedSegUpdates = newAllocation;
  }

  SegmentUpdateInfo* info = &(cell->segmentUpdates[cell->numSegUpdates]);
  initSegmentUpdateInfo(info, cell, segmentID, previous, newSynapses);
  cell->numSegUpdates += 1;

  return info;
}

/**
 * This function reinforces each segment in this Cell's SegmentUpdateInfo.
 * Using the segmentUpdateInfo, the following changes are
 * performed. If positiveReinforcement is true then synapses on the active
 * list get their permanence counts incremented by permanenceInc. All other
 * synapses get their permanence counts decremented by permanenceDec. If
 * positiveReinforcement is false, then synapses on the active list get
 * their permanence counts decremented by permanenceDec. After this step,
 * any synapses in segmentUpdate that do yet exist get added with a permanence
 * count of initialPerm. These new synapses are randomly chosen from the
 * set of all cells that have learnState output = 1 at time step t.
 */
void applyCellSegmentUpdates(Cell* cell, bool positiveReinforcement) {
  int i;
  for(i=0; i<cell->numSegUpdates; ++i) {
    SegmentUpdateInfo* info = &(cell->segmentUpdates[i]);
    applySegmentUpdates(info, positiveReinforcement);

    /*delete segment update instances after they are applied*/
    deleteSegmentUpdateInfo(info);
  }

  /*clear list of segmentUpdates.  keep memory allocated, simply roll the
  //count back to 0 and later call initSegmentUpdateInfo on existing
  //objects to reinitialize for reuse.*/
  cell->numSegUpdates = 0;
}

/**
 * For this cell (at t-1 if previous=True else at t), find the segment (only
 * consider segments that predict activation in exactly
 * <code>numPredictionSteps</code> number of time steps) with the largest
 * number of active synapses.<p>
 * This routine is aggressive in finding the best match. The permanence
 * value of synapses is allowed to be below connectedPerm.
 * The number of active synapses is allowed to be below activationThreshold,
 * but must be above minThreshold. The routine returns that segment.
 * If no segments are found, then null is returned.
 * @param numPredictionSteps only consider segments that are predicting
 *  cell activation to occur in exactly this many time steps from now.
 * @param previous if true only consider active segments from t-1 else
 *  consider active segments right now.
 */
Segment* getBestMatchingSegment(Cell* cell, int numPredictionSteps, bool previous,
    int* segmentID) {
  Segment* bestSegment = NULL;
  int bestSynapseCount = MIN_SYNAPSES_PER_SEGMENT_THRESHOLD;
  int i;
  for(i=0; i<cell->numSegments; ++i) {
    Segment* seg = &(cell->segments[i]);
    if(seg->predictionSteps==numPredictionSteps) {
      int synCount = 0;
      if(previous)
        synCount = seg->numPrevActiveAllSyns;
      else
        synCount = seg->numActiveAllSyns;

      if(synCount > bestSynapseCount) {
        bestSynapseCount = synCount;
        bestSegment = seg;
        *segmentID = i;
      }
    }
  }
  return bestSegment;
}

/**
 *  For this cell in the previous time step (t-1) find the segment with the
 *  largest number of active synapses.<p>
 *  However only consider segments that predict activation in the number of
 *  time steps of the active segment of this cell with the least number of
 *  steps until activation + 1.  For example if right now this cell is being
 *  predicted to occur in t+2 at the earliest, then we want to find the best
 *  segment from last time step that would predict for t+3.<p>
 *  This routine is aggressive in finding the best match. The permanence
 *  value of synapses is allowed to be below connectedPerm.
 *  The number of active synapses is allowed to be below activationThreshold,
 *  but must be above minThreshold. The routine returns that segment.
 *  If no segments are found, then null is returned.
 *  @return the best matching previous segment, or null if none found.
 */
Segment* getBestMatchingPreviousSegment(Cell* cell, int* segmentID) {
  return getBestMatchingSegment(cell, cell->predictionSteps+1, true, segmentID);
}

