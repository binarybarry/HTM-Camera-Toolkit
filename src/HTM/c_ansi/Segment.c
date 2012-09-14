/*
 * Segment.c
 *
 * Represent a single dendrite segment that forms synapses (connections) to
 * other cells. Each segment also maintains a boolean flag, sequenceSegment,
 * indicating whether the segment predicts feed-forward input on the next
 * time step. Segments can be either proximal or distal (for spatial pooling
 * or temporal pooling respectively) however the class object itself does not
 * need to know which it ultimately is as they behave identically.  Segments
 * are considered 'active' if enough of its existing synapses are connected
 * and individually active.
 *
 *  Created on: Jul 19, 2012
 *      Author: barry
 */

#include <stdlib.h>
#include <stdio.h>
#include <stdbool.h>
#include "Region.h"

/**
 * Initialize the Segment with the specified segment activation threshold.
 */
void initSegment(Segment* seg, int segActiveThreshold) {
  seg->numSynapses = 0;
  seg->allocatedSynapses = 10;
  seg->synapses = malloc(seg->allocatedSynapses * sizeof(Synapse));
  seg->isSequence = false;
  seg->segActiveThreshold = segActiveThreshold;
  seg->isActive = false;
  seg->wasActive = false;
  seg->numActiveAllSyns = 0;
  seg->numPrevActiveAllSyns = 0;
  seg->numActiveConnectedSyns = 0;
  seg->numPrevActiveConnectedSyns = 0;
  seg->predictionSteps = 0;
}

/**
 * Free the memory that has been allocated by fields within the Segment
 * structure.  In this case, free the array of synapses that were
 * allocated.  This function does NOT free the Segment itself.
 */
void deleteSegment(Segment* seg) {
  free(seg->synapses);
  seg->synapses = NULL;
  seg->numSynapses = 0;
}

/**
 * Advance this segment to the next time step.  The current state of this
 * segment (active, number of synapes) will be set as the previous state and
 * the current state will be reset to no cell activity by default until it
 * can be determined.
 */
void nextSegmentTimeStep(Segment* seg) {
  seg->wasActive = seg->isActive;
  seg->isActive = false;
  seg->numPrevActiveAllSyns = seg->numActiveAllSyns;
  seg->numPrevActiveConnectedSyns = seg->numActiveConnectedSyns;

  int i; /*cache "wasConnected" for all synapses*/
  for(i=0; i<seg->numSynapses; ++i) {
    seg->synapses[i].wasConnected = seg->synapses[i].isConnected;
    seg->synapses[i].isConnected = false;
  }
}

/**
 * Process this segment for the current time step.  Processing will determine
 * the set of active synapses on this segment for this time step.  From there
 * we will determine if this segment is active if enough active synapses
 * are present.  This information is then cached for the remainder of the
 * Region's processing for the time step.  When a new time step occurs, the
 * Region will call nextTimeStep() on all cells/segments to cache the
 * information as what was previously active.
 */
void processSegment(Segment* seg) {
  /*cache the isConnected per synapse based on permanence, then
   *count the numbers of active synpases (both connected and total).*/
  int i, nc=0, na=0;
  for(i=0; i<seg->numSynapses; ++i) {
     Synapse* syn = &(seg->synapses[i]);
     syn->isConnected = (syn->permanence >= CONNECTED_PERM);

    if(syn->inputSource->isActive) {
      nc += syn->isConnected;
      na++;
    }
    /*if(isSynapseActive(syn, true))
      ++nc;
    if(isSynapseActive(syn, false))
      ++na;*/
  }

  seg->numActiveConnectedSyns = nc;
  seg->numActiveAllSyns = na;
  seg->isActive = seg->numActiveConnectedSyns >= seg->segActiveThreshold;
}

/**
 * Define the number of time steps in the future an activation will occur
 * in if this segment becomes active.  For example if the segment is intended
 * to predict activation in the very next time step (t+1) then this value is
 * 1. If the value is 2 this segment is said to predict its Cell will activate
 * in 2 time steps (t+2) etc.  By definition if a segment is a sequence
 * segment it has a value of 1 for prediction steps.
 * @param steps the number of steps into the future an activation will occur
 * in if this segment becomes active.
 */
void setNumPredictionSteps(Segment* seg, int steps) {
  if(steps < 1) steps = 1;
  if(steps > MAX_TIME_STEPS) steps = MAX_TIME_STEPS;
  seg->predictionSteps = steps;/*min(max(1, steps), MAX_TIME_STEPS);*/
  seg->isSequence = seg->predictionSteps==1;
}

/**
 * Create a new synapse for this segment attached to the specified input source.
 * @param inputSource: the input source of the synapse to create.
 * @return the newly created synapse.
 */
Synapse* createSynapse(Segment* seg, Cell* inputSource, int initPerm) {
  /*if synapse array is full, need to increase capacity to add more*/
  if(seg->numSynapses == seg->allocatedSynapses) {
    int newAllocation = seg->allocatedSynapses*2;
    seg->synapses = realloc(seg->synapses, newAllocation * sizeof(Synapse));
    seg->allocatedSynapses = newAllocation;
  }

  initSynapse(&seg->synapses[seg->numSynapses], inputSource, initPerm);
  seg->numSynapses += 1;

  return &(seg->synapses[seg->numSynapses-1]);
}

/**
 * Update (increase or decrease) all permanence values of each synapse on
 * this segment.
 */
void updateSegmentPermanences(Segment* seg, bool increase) {
  int i;
  for(i=0; i<seg->numSynapses; ++i) {
    Synapse* syn = &(seg->synapses[i]);
    if(increase)
      increaseSynapsePermanence(syn, 0);
    else
      decreaseSynapsePermanence(syn, 0);
  }
}

/**
 * This routine returns true if the number of connected synapses on this segment
 * that were active due to learning states at time t-1 is greater than activationThreshold.
 */
bool wasSegmentActiveFromLearning(Segment* seg) {
  int i, c=0;
  for(i=0; i<seg->numSynapses; ++i) {
    if(wasSynapseActiveFromLearning(&(seg->synapses[i])))
      ++c;
  }
  return c >= seg->segActiveThreshold;
}
