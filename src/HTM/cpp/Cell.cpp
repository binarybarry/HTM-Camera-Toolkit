/*
 * Cell.cpp
 *
 *  Created on: Sep 22, 2011
 *      Author: barry
 *
 * Represents an HTM sequence cell that belongs to a given Column.
 */

#include <stdio.h>
#include <vector>
#include <set>
#include "Region.h"

int MIN_SYNAPSES_PER_SEGMENT_THRESHOLD = 1;

/**
 *  Create a new Cell belonging to the specified Column. The index is an
 *  integer id to distinguish this Cell from others in the Column.
 */
Cell::Cell() {
  _isActive = false;
  _wasActive = false;
  _isPredicting = false;
  _wasPredicted = false;
  _isLearning = false;
  _wasLearning = false;
}

Cell::~Cell() {
  for(unsigned int i=0; i<_segments.size(); ++i)
    delete _segments[i];
  _segments.clear();
  for(std::list<SegmentUpdateInfo*>::iterator iter = _segmentUpdates.begin();
      iter!=_segmentUpdates.end(); ++iter) {
    delete (*iter); //TODO better way to do this?
  }
  _segmentUpdates.clear();
}

Region* Cell::getRegion() {
  return _column->getRegion();
}

/**
 *  Advance this cell to the next time step. The current state of this cell
 *  (active, learning, predicting) will be set as the previous state and the current
 *  state will be reset to no cell activity by default until it can be determined.
 */
void Cell::nextTimeStep() {
  _wasActive = _isActive;
  _wasPredicted = _isPredicting;
  _wasLearning = _isLearning;
  _isActive = false;
  _isPredicting = false;
  _isLearning = false;
}

/**
 *  Create a new segment for this Cell. The new segment will initially connect to
 *  at most newSynapseCount synapses randomly selected from the set of cells that
 *  were in the learning state at t-1 (specified by the learningCells parameter).
 *  @param learningCells: the set of available learning cells to add to the segment.
 *  @return the segment that was just created.
 */
Segment* Cell::createSegment(std::set<Cell*>& learningCells) {
  std::set<Synapse*> added;
  Segment* newSegment = new Segment(_column->getRegion()->getSegActiveThreshold());
  newSegment->createSynapsesToLearningCells(learningCells, added);
  _segments.push_back(newSegment);
  return newSegment;
}

/**
 *  For this cell, return a segment that was active in the previous time
 *  step. If multiple segments were active, sequence segments are given preference.
 *  Otherwise, segments with most activity are given preference.
 */
Segment* Cell::getPreviousActiveSegment() {
  std::vector<Segment*> activeSegs;
  for(unsigned int i=0; i<_segments.size(); ++i) {
    if(_segments[i]->wasActive())
      activeSegs.push_back(_segments[i]);
  }

  if(activeSegs.size()==1) //if only 1 active segment, return it
    return activeSegs[0];

  if(activeSegs.size() > 1) {
    //if >1 active segments, sequence segments given priority
    std::vector<Segment*> sequenceSegs;
    for(unsigned int i=0; i<activeSegs.size(); ++i) {
      if(activeSegs[i]->isSequence()) {
        sequenceSegs.push_back(activeSegs[i]);
      }
    }

    if(sequenceSegs.size()==1)
      return sequenceSegs[0];
    else if(sequenceSegs.size() > 1) {
      activeSegs.clear();
      for(unsigned int i=0; i<sequenceSegs.size(); ++i)
        activeSegs.push_back(sequenceSegs[i]);
    }

    //if multiple possible segments, return segment with most activity
    Segment* bestSegment = activeSegs[0];
    int mostActiveSyns = bestSegment->getPrevActiveSynapseCount();
    for(unsigned int i=1; i<activeSegs.size(); ++i) {
      int activeSyns = activeSegs[i]->getPrevActiveSynapseCount();
      if(activeSyns > mostActiveSyns) {
        mostActiveSyns = activeSyns;
        bestSegment = activeSegs[i];
      }
    }
    return bestSegment;
  }

  return NULL;
}

/**
 *  Return a SegmentUpdateInfo object containing proposed changes to the specified
 *  segment.  If the segment is None, then a new segment is to be added, otherwise
 *  the specified segment is updated.  If the segment exists, find all active
 *  synapses for the segment (either at t or t-1 based on the 'previous' parameter)
 *  and mark them as needing to be updated.  If newSynapses is true, then
 *  Region.newSynapseCount - len(activeSynapses) new synapses are added to the
 *  segment to be updated.  The (new) synapses are randomly chosen from the set
 *  of current learning cells (within Region.localityRadius if set).
 *
 *  These segment updates are only applied when the applySegmentUpdates
 *  method is later called on this Cell.
 */
SegmentUpdateInfo* Cell::updateSegmentActiveSynapses(bool previous, Segment* segment,
    bool newSynapses) {
  std::set<Synapse*> activeSyns;
  if(segment!=NULL) {
    if(previous)
      segment->getPrevActiveSynapses(activeSyns);
    else
      segment->getActiveSynapses(activeSyns);
  }

  SegmentUpdateInfo* segmentUpdate =
      new SegmentUpdateInfo(this, segment, activeSyns, newSynapses);
  _segmentUpdates.push_back(segmentUpdate);
  return segmentUpdate;
}

/**
 *  This function reinforces each segment in this Cell's SegmentUpdateInfo.
 *  Using the segmentUpdateInfo, the following changes are
 *  performed. If positiveReinforcement is true then synapses on the active
 *  list get their permanence counts incremented by permanenceInc. All other
 *  synapses get their permanence counts decremented by permanenceDec. If
 *  positiveReinforcement is false, then synapses on the active list get
 *  their permanence counts decremented by permanenceDec. After this step,
 *  any synapses in segmentUpdate that do yet exist get added with a permanence
 *  count of initialPerm. These new synapses are randomly chosen from the
 *  set of all cells that have learnState output = 1 at time step t.
 */
void Cell::applySegmentUpdates(bool positiveReinforcement) {
  for(std::list<SegmentUpdateInfo*>::iterator iter = _segmentUpdates.begin();
      iter!=_segmentUpdates.end(); ++iter) {
    SegmentUpdateInfo* segInfo = (*iter);
    Segment* segment = segInfo->getSegment();

    if(segment!=NULL) {
      if(positiveReinforcement)
        segment->updatePermanences(segInfo->getActiveSynapses());
      else
        segment->decreasePermanences(segInfo->getActiveSynapses());
    }

    //add new synapses (and new segment if necessary)
    if(segInfo->getAddNewSynapses() && positiveReinforcement) {
      if(segment==NULL) {
        if(segInfo->numLearningCells() > 0)//only add if learning cells available
          segment = segInfo->createCellSegment();
      }
      else if(segInfo->numLearningCells() > 0) {
        //add new synapses to existing segment
        segInfo->createSynapsesToLearningCells();
      }
    }
  }

  //delete segment update instances after they are applied
  for(std::list<SegmentUpdateInfo*>::iterator iter = _segmentUpdates.begin();
      iter!=_segmentUpdates.end(); ++iter) {
    delete (*iter); //TODO test if this is ok
  }
  _segmentUpdates.clear();
}

/**
 *  For this cell (at t-1 if previous=True else at t), find the segment (only
 *  consider sequence segments if isSequence is True, otherwise only consider
 *  non-sequence segments) with the largest number of active synapses.
 *  This routine is aggressive in finding the best match. The permanence
 *  value of synapses is allowed to be below connectedPerm.
 *  The number of active synapses is allowed to be below activationThreshold,
 *  but must be above minThreshold. The routine returns that segment.
 *  If no segments are found, then None is returned.
 */
Segment* Cell::getBestMatchingSegment(bool isSequence, bool previous) {
  Segment* bestSegment = NULL;
  int bestSynapseCount = MIN_SYNAPSES_PER_SEGMENT_THRESHOLD;
  for(unsigned int i=0; i<_segments.size(); ++i) {
    if(_segments[i]->isSequence()==isSequence) {
      int synCount = 0;
      if(previous)
        synCount = _segments[i]->getPrevActiveSynapseCount(false);
      else
        synCount = _segments[i]->getActiveSynapseCount(false);

      if(synCount > bestSynapseCount) {
        bestSynapseCount = synCount;
        bestSegment = _segments[i];
      }
    }
  }
  return bestSegment;
}

/**
 *  Return true if this cell has a currently active sequence segment.
 */
bool Cell::hasActiveSequenceSegment() {
  for(unsigned int i=0; i<_segments.size(); ++i) {
    if(_segments[i]->isActive() && _segments[i]->isSequence())
      return true;
  }
  return false;
}

