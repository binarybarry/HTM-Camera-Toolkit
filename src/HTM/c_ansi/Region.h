/*
 * Region.h
 *
 *  Created on: Jul 21, 2012
 *      Author: barry
 */

#ifndef REGION_H_
#define REGION_H_

#include "Column.h"

#define min(X, Y)  ((X) < (Y) ? (X) : (Y))
#define max(X, Y)  ((X) > (Y) ? (X) : (Y))

typedef struct RegionType {
  int inputWidth, inputHeight;
  int localityRadius;
  int cellsPerCol;
  int segActiveThreshold;
  int newSynapseCount;

  float pctInputPerCol;
  float pctMinOverlap;
  float pctLocalActivity;

  bool spatialHardcoded;
  bool spatialLearning;
  bool temporalLearning;

  int width, height;
  float xSpace, ySpace;

  Column* columns;
  int numCols;

  float minOverlap;
  float inhibitionRadius;
  int desiredLocalActivity;

  char* inputData;
  int nInput;
  Cell* inputCells;
  int iters;
} Region;

Region* newRegionHardcoded(int inputSizeX, int inputSizeY, int localityRadius,
    int cellsPerCol, int segActiveThreshold, int newSynapseCount,
    char* inputData);
Region* newRegion(int inputSizeX, int inputSizeY, int colGridSizeX, int colGridSizeY,
    float pctInputPerCol, float pctMinOverlap, int localityRadius,
    float pctLocalActivity, int cellsPerCol, int segActiveThreshold,
    int newSynapseCount, char* inputData);
void deleteRegion(Region* region);
void getColumnPredictions(Region* region, char* outData);
void getLastAccuracy(Region* region, float* result);
int numRegionSegments(Region* region, int predictionSteps);
int numRegionActiveColumns(Region* region);
void runOnce(Region* region);

void performSpatialPooling(Region* region);
void performTemporalPooling(Region* region);

#endif /* REGION_H_ */
