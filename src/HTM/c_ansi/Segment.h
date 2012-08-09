/*
 * Segment.h
 *
 *  Created on: Jul 19, 2012
 *      Author: barry
 */

#ifndef SEGMENT_H_
#define SEGMENT_H_

#include <stdbool.h>
#include "Synapse.h"

#define MAX_TIME_STEPS 10 /*most prediction steps to track*/

/**
 * Represent a single dendrite segment that forms synapses (connections) to
 * other cells. Each segment also maintains a boolean flag, sequenceSegment,
 * indicating whether the segment predicts feed-forward input on the next
 * time step. Segments can be either proximal or distal (for spatial pooling
 * or temporal pooling respectively) however the class object itself does not
 * need to know which it ultimately is as they behave identically.  Segments
 * are considered 'active' if enough of its existing synapses are connected
 * and individually active.
 */
typedef struct SegmentType {
  Synapse* synapses;
  int numSynapses;
  int allocatedSynapses;

  bool isSequence;
  int predictionSteps;
  float segActiveThreshold;

  bool isActive;
  bool wasActive;

  /**
   * Cached counts of how many synapses on this segment are active
   * in the current time step and were active last time step.
   * Store 2 counts of each, either only connected synapses or all synapses
   * regardless of connection state.
   */
  int numActiveConnectedSyns;
  int numPrevActiveConnectedSyns;
  int numActiveAllSyns;
  int numPrevActiveAllSyns;

} Segment;

void initSegment(Segment* seg, int segActiveThreshold);
void deleteSegment(Segment* seg);
void nextSegmentTimeStep(Segment* seg);
void processSegment(Segment* seg);
void setNumPredictionSteps(Segment* seg, int steps);
Synapse* createSynapse(Segment* seg, struct CellType* inputSource, float initPerm);
void adaptSegmentPermanences(Segment* seg);
void updateSegmentPermanences(Segment* seg, bool increase);
bool wasSegmentActiveFromLearning(Segment* seg);

#endif /* SEGMENT_H_ */
