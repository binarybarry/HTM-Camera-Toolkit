/*
 * SegmentUpdateInfo.c
 *
 * This data structure holds three pieces of information required to update
 *  a given segment:
 *  a) segment reference (None if it's a new segment),
 *  b) a list of existing active synapses, and
 *  c) a flag indicating whether this segment should be marked as a sequence
 *     segment (defaults to false).
 *  The structure also determines which learning cells (at this time step)
 *  are available to connect (add synapses to) should the segment get updated.
 *  If there is a locality radius set on the Region, the pool of learning cells
 *  is restricted to those with the radius.
 *
 *  Created on: Jul 22, 2012
 *      Author: barry
 */

#include <stdio.h>
#include <stdlib.h>
#include "Region.h"

/**
 * Randomly sample m values from the Cell array of length n (m < n).
 * Runs in O(2m) worst case time.  Result is returned as a newly allocated
 * array of length m containing the randomly chosen pointers.
 */
Cell** randomSample(Cell** cells, int n, int m) {
  Cell** ss = malloc(m * sizeof(Cell*));
  int i, j, k;
  for(i=n-m, k=0; i<n; ++i, ++k) {
    int pos = rand() % (i+1);
    Cell* item = cells[pos];

    /*if(subset ss contains item already) then use item[i] instead*/
    bool contains = false;
    for(j=0; j<k; ++j) {
      Cell* ss0 = ss[j];
      if(ss0 == item) {
        contains = true;
        break;
      }
    }
    if(contains)
      ss[k] = cells[i];
    else
      ss[k] = item;
  }
  return ss;
}

/**
 * Allocate a new SegmentUpdateInfo using the given parameters.
 */
void initSegmentUpdateInfo(SegmentUpdateInfo* info, Cell* cell, int segmentID,
    bool previous, bool addNewSynapses) {
  info->activeSynapseIDs = NULL;
  info->learningCells = NULL;

  /*if segment non-null, copy pointers to active synapses within the segment
  //from either current or previous time step*/
  int i,s;
  Segment* segment = NULL;
  if(segmentID >= 0)
    segment = &(cell->segments[segmentID]);
  if(segment!=NULL) {
    if(previous) {
      info->numActiveSyns = segment->numPrevActiveConnectedSyns;
      info->activeSynapseIDs = malloc(info->numActiveSyns * sizeof(int));
      /*TODO check for NULL failed memory allocation?*/
      for(i=0, s=0; i<segment->numSynapses; ++i) {
        if(wasSynapseActive(&(segment->synapses[i]), true)) {
          info->activeSynapseIDs[s] = i;/*&(segment->synapses[i]);*/
          ++s;
        }
      }
      if(info->numActiveSyns != s)/*DEBUG check*/
        printf("(p)mismatch nas vs s: (%i %i)", info->numActiveSyns, s);
    }
    else {
      info->numActiveSyns = segment->numActiveConnectedSyns;
      info->activeSynapseIDs = malloc(segment->numActiveConnectedSyns * sizeof(int));
      for(i=0, s=0; i<segment->numSynapses; ++i) {
        if(isSynapseActive(&(segment->synapses[i]), true)) {
          info->activeSynapseIDs[s] = i;/*&(segment->synapses[i]);*/
          ++s;
        }
      }
      if(info->numActiveSyns != s)/*DEBUG check*/
        printf("mismatch nas vs s: (%i %i)", info->numActiveSyns, s);
    }
  }

  info->cell = cell;
  info->segmentID = segmentID;
  info->addNewSynapses = addNewSynapses;
  info->numPredictionSteps = 1;

  Region* region = cell->column->region;
  Column* ownColumn = cell->column;

  /*reserve space for storing list of current learning cells*/
  int numLearnCells = 0;
  int allocatedLearnCells = 10;
  Cell** learningCells = malloc(allocatedLearnCells * sizeof(Cell*));

  if(addNewSynapses) {
    /* Need array of all learningCells in this time step.
     * then need subset of only learningCells we are not connected to.
     * then need a random subset of this for potential add.*/

    /* Get all destination Cells this segment is connected to.
    // Only consider Cells within given radius, and which were learning in t-1
    //   and are not already connected as destinations*/

    int minY = 0;
    int maxY = region->height-1;
    int minX = 0;
    int maxX = region->width-1;
    if(region->localityRadius > 0) {
      /*TODO implement locality radius*/
    }

    /*do not add >1 synapse to the same cell on a given segment*/
    int x,y;
    for(x=minX; x<=maxX; ++x) {
      for(y=minY; y<=maxY; ++y) {
        Column* col = &(region->columns[(y*region->width)+x]);
        if(col==ownColumn) {
          /*printf("skip own column (%d,%d)\n", x,y);*/
          continue;
        }
        for(i=0; i<col->numCells; ++i) {
          Cell* cell = &(col->cells[i]);
          if(cell->wasLearning) {/* && segCells.count(cell)==0) {*/
            /*TODO is there is more optimal way to check this?
            //if segment is non-null, check if this cell is already connected*/
            bool ok = true;
            if(segment!=NULL) {
              for(s=0; s<segment->numSynapses; ++s) {
                Cell* scell = segment->synapses[s].inputSource;
                if(scell==cell) {
                  ok = false;
                  break;
                }
              }
            }

            if(ok) {
              /*printf("learningCell added (%d,%d) %d\n", x, y, i);
              //if array is full, need to increase capacity to add more*/
              if(numLearnCells == allocatedLearnCells) {
                int newAllocation = allocatedLearnCells*2;
                learningCells = realloc(learningCells, newAllocation * sizeof(Cell*));
                allocatedLearnCells = newAllocation;
              }
              learningCells[numLearnCells] = cell;
              numLearnCells += 1;
            }
          }
        }
      }
    }
  }

  int synCount = region->newSynapseCount;
  if(segment!=NULL)
    synCount = max(0, synCount-info->numActiveSyns);
  synCount = min(numLearnCells, synCount);/*clamp at # of learn cells*/
  /*printf("synCount = %d\n", synCount);*/

  /*randomly choose synCount learning cells to add connections to*/
  info->numLearningCells = synCount;
  if(numLearnCells > 0 && synCount > 0) {
    Cell** ss = randomSample(learningCells, numLearnCells, synCount);
    info->learningCells = ss;
  }

  free(learningCells); /*free the temporary learning cell pointer array*/
}

/**
 * Free the memory that has been allocated by fields within the SegmentUpdateInfo
 * structure.  In this case, free the array of learningCells and activeSynapses that
 * were allocated.  This function does NOT free the SegmentUpdateInfo itself.
 */
void deleteSegmentUpdateInfo(SegmentUpdateInfo* info) {
  if(info->activeSynapseIDs!=NULL)
    free(info->activeSynapseIDs);
  info->activeSynapseIDs = NULL;
  info->numActiveSyns = 0;

  if(info->learningCells!=NULL)
    free(info->learningCells);
  info->learningCells = NULL;
  info->numLearningCells = 0;
}

/**
 * Create new synapse connections to the segment to be updated using
 * the set of learning cells in this update info.
 */
void createSynapsesToLearningCells(SegmentUpdateInfo* info, Segment* seg) {
  /*info->numAddedSyns = info->numLearningCells;
  info->allocatedAddedSyns = info->numAddedSyns;
  info->addedSynapses = malloc(info->allocatedAddedSyns * sizeof(Synapse*));*/

  int i;
  for(i=0; i<info->numLearningCells; ++i) {
    Cell* cell = info->learningCells[i];
    Synapse* syn = createSynapse(seg, cell, INITIAL_PERMANENCE);
    /*info->addedSynapses[i] = syn;*/
  }
}

/**
 * Create a new segment on the update cell using connections from
 * the set of learning cells for the update info.
 *
 * Create a new segment for the Cell being updated in the SegmentUpdateInfo.
 * The new segment will initially connect to at most newSynapseCount synapses
 * randomly selected from the set of cells that were in the learning state
 * at t-1 (specified by the learningCells parameter).
 * @param info: the SegmenuUpdateInfo that defines the new segment.
 * @return the segment that was just created.
 */
Segment* createCellSegmentFromInfo(SegmentUpdateInfo* info) {
  /*"seg->createSynapsesToLearningCells(..)"
  //Create numSynapses new synapses for this segment attached to the specified
  //set of learning cells.*/
  Segment* seg = createCellSegment(info->cell);
  setNumPredictionSteps(seg, info->numPredictionSteps);
  createSynapsesToLearningCells(info, seg);
  return seg;
}

/**
 * Update (increase or decrease based on whether the synapse is active)
 * all permanence values of each of the synapses in the specified set.
 */
void updateInfoPermanences(SegmentUpdateInfo* info) {
  /*decrease all Segment synapses, then increase active's x2*/
  Segment* segment = &(info->cell->segments[info->segmentID]);
  unsigned int i;
  for(i = 0; i<segment->numSynapses; ++i) {
    Synapse* syn = &(segment->synapses[i]);
    decreaseSynapsePermanence(syn, 0);
  }

  for(i=0; i<info->numActiveSyns; ++i) {
    Synapse* syn = &(segment->synapses[info->activeSynapseIDs[i]]);
    increaseSynapsePermanence(syn, PERMANENCE_INC*2);
  }
}

/**
 * Decrease the permanences of each of the synapses in the set of
 * active synapses that happen to be on this segment.
 */
void decreaseInfoPermanences(SegmentUpdateInfo* info) {
  Segment* segment = &(info->cell->segments[info->segmentID]);
  int i;
  for(i=0; i<info->numActiveSyns; ++i) {
    Synapse* syn = &(segment->synapses[info->activeSynapseIDs[i]]);
    decreaseSynapsePermanence(syn, 0);
  }
}

/**
 * Apply the segment updates in the SegmentUpdateInfo.  If a segment was assigned
 * then update the permanences of its synapses (increase if positiveReinforcement
 * is true else decrease).  If the new synapses flag is set then add new synapses
 * to the segment or create a new segment entirely if no segment was assigned.
 */
void applySegmentUpdates(SegmentUpdateInfo* info, bool positiveReinforcement) {
  Segment* segment = NULL;
  if(info->segmentID >= 0)
    segment = &(info->cell->segments[info->segmentID]);
  if(segment!=NULL) {
    if(positiveReinforcement)
      updateInfoPermanences(info);
    else
      decreaseInfoPermanences(info);
  }

  /*add new synapses (and new segment if necessary)*/
  if(info->addNewSynapses && positiveReinforcement) {
    if(segment==NULL) {
      if(info->numLearningCells > 0)/*only add if learning cells available*/
        segment = createCellSegmentFromInfo(info);
    }
    else if(info->numLearningCells > 0) {
      createSynapsesToLearningCells(info, segment);
    }
  }
}

