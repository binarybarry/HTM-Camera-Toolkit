/*
 * SegmentUpdateInfo.h
 *
 *  Created on: Jul 22, 2012
 *      Author: barry
 */

#ifndef SEGMENTUPDATEINFO_H_
#define SEGMENTUPDATEINFO_H_

#include <stdbool.h>

typedef struct SegmentUpdateInfoType {
  struct CellType* cell;
  int segmentID;/*Segment* segment;*/
  int numPredictionSteps;

  int* activeSynapseIDs;/*Synapse** activeSynapses;*/
  int numActiveSyns;

  struct CellType** learningCells;
  int numLearningCells;
  bool addNewSynapses;

  /*Synapse** addedSynapses;
  int numAddedSyns;
  int allocatedAddedSyns;*/
} SegmentUpdateInfo;

void randomSample(struct CellType** cells, int n, struct CellType** ssCells, int m);
void initSegmentUpdateInfo(SegmentUpdateInfo* info, struct CellType* cell,
    int segmentID, bool previous, bool addNewSynapses);
void deleteSegmentUpdateInfo(SegmentUpdateInfo* info);
void applySegmentUpdates(SegmentUpdateInfo* info, bool positiveReinforcement);

#endif /* SEGMENTUPDATEINFO_H_ */
