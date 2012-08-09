/*
 * Region.c
 *
 *  Code to represent an entire Hierarchical Temporal Memory (HTM) Region of
 *  Columns that implement Numenta's new Cortical Learning Algorithms (CLA).
 *
 *  The Region is defined by a matrix of columns, each of which contains several
 *  cells.  The main idea is that given a matrix of input bits, the Region will
 *  first sparsify the input such that only a few Columns will become 'active'.
 *  As the input matrix changes over time, different sets of Columns will
 *  become active in sequence.  The Cells inside the Columns will attempt
 *  to learn these temporal transitions and eventually the Region will be
 *  able to make predictions about what may happen next given what has happened
 *  in the past.
 *
 *  For (much) more information, visit www.numenta.com.
 *
 *  SpatialPooling snippet from the Numenta docs:
 *
 *  The code computes activeColumns(t) = the list of columns that win due to
 *  the bottom-up input at time t. This list is then sent as input to the
 *  temporal pooler routine.
 *
 *  Phase 1: compute the overlap with the current input for each column
 *  Phase 2: compute the winning columns after inhibition
 *  Phase 3: update synapse permanence and internal variables
 *
 *  1) Start with an input consisting of a fixed number of bits. These bits might represent
 *     sensory data or they might come from another region lower in the hierarchy.
 *  2) Assign a fixed number of columns to the region receiving this input. Each column has
 *     an associated dendrite segment. Each dendrite segment has a set of potential synapses
 *     representing a subset of the input bits. Each potential synapse has a permanence value.
 *     Based on their permanence values, some of the potential synapses will be valid.
 *  3) For any given input, determine how many valid synapses on each column are
 *     connected to active input bits.
 *  4) The number of active synapses is multiplied by a 'boosting' factor which is
 *     dynamically determined by how often a column is active relative to its neighbors.
 *  5) The columns with the highest activations after boosting disable all but a fixed
 *     percentage of the columns within an inhibition radius. The inhibition radius is
 *     itself dynamically determined by the spread (or 'fan-out') of input bits. There is
 *     now a sparse set of active columns.
 *  6) For each of the active columns, we adjust the permanence values of all the potential
 *     synapses. The permanence values of synapses aligned with active input bits are
 *     increased. The permanence values of synapses aligned with inactive input bits are
 *     decreased. The changes made to permanence values may change some synapses from being
 *     valid to not valid, and vice-versa.
 *
 *  Created on: Jul 21, 2012
 *      Author: barry
 */

#include <math.h>
#include <stdlib.h>
#include <stdio.h>
#include "Region.h"

bool DEBUG = true;
bool HARDCODE_SPATIAL = true;

/**
 * The radius of the average connected receptive field size of all the columns.
 * The connected receptive field size of a column includes only the connected
 * synapses (those with permanence values >= connectedPerm). This is used to
 * determine the extent of lateral inhibition between columns.
 * @return the average connected receptive field size (in column grid space).
 */
float averageReceptiveFieldSize(Region* region) {
  int i,j;
  int n = 0;
  double sum = 0.0;
  for(i=0; i<region->numCols; ++i) {
    Column* col = &(region->columns[i]);
    Segment* seg = col->proximalSegment;
    /*loop over all connected proximal synapses for this column*/
    for(j=0; j<seg->numSynapses; ++j) {
      Synapse* syn = &(seg->synapses[j]);
      if(syn->isConnected) {
        /*TODO need syn->inputCell->ix() from proximal cell, not distal cell*/
        double dx = col->ix - col->cx;/*syn->inputSource->ix()*/
        double dy = col->iy - col->cy;/*syn.getCellIY();*/
        double d = sqrt(dx*dx + dy*dy);
        sum += (d / region->xSpace);
        n++;
      }
    }
  }
  return (float)(sum / n);
}

/**
 * Region initialization using hard-coded spatial pooler.  Hard-coded means
 * that input bits are mapped directly to columns.  In other words the normal
 * spatial pooler is disabled and we instead assume the input sparsification
 * has already been decided by some preprocessing code outside the Region.
 * It is then assumed (though not checked) that the input array will have
 * only a sparse number of "1" values that represent the active columns
 * for each time step.<p>
 *
 * With hardcoded the Region will create a matching number of Columns to
 * mirror the size of the input array.  Locality radius may still be
 * defined as it is still used by the temporal pooler.  If non-zero it will
 * restrict temporal segments from connecting further than r number of
 * columns away.
 *
 * @param inputSizeX size of input data matrix from the external source.
 * @param inputSizeY size of input data matrix from the external source.
 * @param localityRadius Furthest number of columns away to allow distal synapses.
 * @param cellsPerCol Number of (temporal context) cells to use for each Column.
 * @param segActiveThreshold Number of active synapses to activate a segment.
 * @param newSynapseCount number of new distal synapses added if none activated during
 *  learning.
 * @param inputData the array to be used for input data bits.  The contents
 *  of this array must be externally updated between time steps (between
 *  calls to Region.runOnce()).
 */
Region* newRegionHardcoded(int inputSizeX, int inputSizeY, int localityRadius,
    int cellsPerCol, int segActiveThreshold, int newSynapseCount,
    char* inputData) {
  Region* region = malloc(sizeof(Region));

  region->inputWidth = inputSizeX;
  region->inputHeight = inputSizeY;
  region->iters = 0;
  region->inputData = inputData;

  region->localityRadius = localityRadius;
  region->cellsPerCol = cellsPerCol;
  region->segActiveThreshold = segActiveThreshold;
  region->newSynapseCount = newSynapseCount;

  region->width = inputSizeX;
  region->height = inputSizeY;
  region->xSpace = 1.0;
  region->ySpace = 1.0;

  /*Create the columns based on the size of the input data to connect to.*/
  region->numCols = region->width * region->height;
  region->columns = malloc(region->numCols * sizeof(Column));
  /*TODO check for NULL on allocation fail*/
  int cx,cy;
  for(cx=0; cx<region->width; ++cx) {
    for(cy=0; cy<region->height; ++cy) {
      initColumn(&(region->columns[(cy*region->width)+cx]), region,
          cx,cy, cx,cy);
    }
  }

  region->pctInputPerCol = 1.0f / region->numCols;
  region->pctMinOverlap = 1.0f;
  region->pctLocalActivity = 1.0f;
  region->minOverlap = 1.0f;
  region->desiredLocalActivity = 1;

  /*region->spatialHardcoded = true; TODO*/
  region->spatialLearning = false;
  region->temporalLearning = true;

  return region;
}

/**
 * Region Initialization (from Numenta docs):
 * Prior to receiving any inputs, the region is initialized by computing a list of initial
 * potential synapses for each column. This consists of a random set of inputs selected
 * from the input space. Each input is represented by a synapse and assigned a random
 * permanence value. The random permanence values are chosen with two criteria.
 * First, the values are chosen to be in a small range around connectedPerm (the minimum
 * permanence value at which a synapse is considered "connected"). This enables potential
 * synapses to become connected (or disconnected) after a small number of training
 * iterations. Second, each column has a natural center over the input region, and the
 * permanence values have a bias towards this center (they have higher values near
 * the center).
 *
 * In addition to this I have added a concept of Locality Radius, which is an
 * additional parameter to control how far away synapse connections can be made
 * instead of allowing connections anywhere.  The reason for this is that in the
 * case of video images I wanted to experiment with forcing each Column to only
 * learn on a small section of the total input to more effectively learn lines or
 * corners in a small section without being 'distracted' by learning larger patterns
 * in the overall input space (which hopefully higher hierarchical Regions would
 * handle more successfully).  Passing in 0 for locality radius will mean no restriction
 * which will more closely follow the Numenta doc if desired.
 *
 * @param inputSize: (x,y) size of input data matrix from the external source.
 * @param colGridSize: (x,y) number of Columns to create to represent this Region.
 * @param pctInputPerCol: Percent of input bits each Column has potential synapses for.
 * @param pctMinOverlap: Minimum percent of column's synapses for column to be considered.
 * @param localityRadius: Furthest number of columns away to allow distal synapses.
 * @param pctLocalActivity: Approximate percent of Columns within locality radius to be
 *  winners after inhibition.
 * @param cellsPerCol: Number of (temporal context) cells to use for each Column.
 * @param segActiveThreshold: Number of active synapses to activate a segment.
 * @param newSynapseCount: number of new distal synapses added if none activated during
 *  learning.
 */
Region* newRegion(int inputSizeX, int inputSizeY, int colGridSizeX, int colGridSizeY,
    float pctInputPerCol, float pctMinOverlap, int localityRadius,
    float pctLocalActivity, int cellsPerCol, int segActiveThreshold,
    int newSynapseCount) {
  printf("Constructing Region...\n");

  Region* region = malloc(sizeof(Region));

  region->inputWidth = inputSizeX;
  region->inputHeight = inputSizeY;
  region->nInput = region->inputWidth * region->inputHeight;
  region->iters = 0;

  region->localityRadius = localityRadius;
  region->cellsPerCol = cellsPerCol;
  region->segActiveThreshold = segActiveThreshold;
  region->newSynapseCount = newSynapseCount;

  region->pctInputPerCol = pctInputPerCol;
  region->pctMinOverlap = pctMinOverlap;
  region->pctLocalActivity = pctLocalActivity;

  region->spatialLearning = false;
  region->temporalLearning = true;

  /*Reduce the number of columns and map centers of input x,y correctly.
  //column grid will be relative to size of input grid in both dimensions*/
  region->width = colGridSizeX;
  region->height = colGridSizeY;
  region->numCols = region->width*region->height;
  region->xSpace = (region->inputWidth-1*1.0) / fmaxf(1.0,(region->width-1));
  region->ySpace = (region->inputHeight-1*1.0) / fmaxf(1.0,(region->height-1));

  /*Create the columns based on the size of the input data to connect to.*/
  region->columns = malloc(region->numCols * sizeof(Column));
  /*TODO check for NULL on allocation fail*/
  int cx,cy;
  for(cx=0; cx<region->width; ++cx) {
    for(cy=0; cy<region->height; ++cy) {
      int srcPosX = roundf(cx*region->xSpace);
      int srcPosY = roundf(cy*region->ySpace);
      initColumn(&(region->columns[(cy*region->width)+cx]), region,
          srcPosX,srcPosY, cx,cy);
    }
  }

/*    #size the output array as double grid for 4-cell, else just pad the first
//    #array dimension for 2 or 3 cell (and same size if just 1-cell)
//    if cellsPerCol==4:
//      outShape = (len(self.columnGrid)*2, len(self.columnGrid[0])*2)
//    else:
//      outShape = (len(self.columnGrid)*cellsPerCol, len(self.columnGrid[0]))
//    self.outData = numpy.zeros(outShape, dtype=numpy.uint8)*/

  /*how far apart are 2 Columns in terms of input space; calc radius from that*/
  float inputRadiusf = region->localityRadius*region->xSpace;

  /*Now connect all potentialSynapses for the Columns*/
  int synapsesPerSegment = 1;
  if(region->localityRadius==0)
    synapsesPerSegment = (region->inputWidth*region->inputHeight) * pctInputPerCol;
  else
    synapsesPerSegment = (inputRadiusf*inputRadiusf) * pctInputPerCol;

  /*The minimum number of inputs that must be active for a column to be
  //considered during the inhibition step.*/
  region->minOverlap = synapsesPerSegment * pctMinOverlap;

  /*int longerSide = max(_inputWidth, _inputHeight);
  //random.seed(42) #same connections each time for easier debugging*/

  int inputRadius = roundf(inputRadiusf);
  int minY = 0;
  int maxY = region->inputHeight-1;
  int minX = 0;
  int maxX = region->inputWidth-1;
  int i;
  for(i=0; i<region->numCols; ++i) {
    if(HARDCODE_SPATIAL) /*no proximal synpases for hardcoded case*/
      break;
    Column* col = &(region->columns[i]);

    /*restrict synapse connections if localityRadius is non-zero*/
    if(region->localityRadius > 0) {
      minY = max(0, col->iy-inputRadius);
      maxY = min(region->inputHeight-1, col->iy+inputRadius);
      minX = max(0, col->ix-inputRadius);
      maxX = min(region->inputWidth-1, col->ix+inputRadius);
    }
    /*TODO connect initial proximal synapses
    //ensure we sample unique input positions to connect synapses to*/
/*    Set<Point> allPos = new HashSet<Point>();
//    for(int x=minX; x<=maxX; ++x) {
//      for(int y=minY; y<=maxY; ++y)
//        allPos.add(new Point(x,y));
//    }
//
//    Set<Point> randPos = new HashSet<Point>();
//    Util.createRandomSubset(allPos, randPos, synapsesPerSegment, rand);
//    for(Point pt : randPos) {
//      InputCell icell = new InputCell(
//          pt.x, pt.y, (pt.y*_inputHeight)+pt.x, _inputData);
//      if(FULL_DEFAULT_SPATIAL_PERMANENCE)
//        col.addProximalSynapse(icell, 1.0f);
//      else {
//        double permanence = Synapse.CONNECTED_PERM +
//                           (Synapse.PERMANENCE_INC*rand.nextGaussian());
//        permanence = Math.max(0.0, permanence);
//        double dx = col.ix()-pt.x;
//        double dy = col.iy()-pt.y;
//        double distance = Math.sqrt((dx*dx) + (dy*dy));
//        double ex = distance / (longerSide*RAD_BIAS_STD_DEV);
//        double localityBias = (RAD_BIAS_PEAK/0.4) * Math.exp((ex*ex)/-2);
//        col.addProximalSynapse(icell, (float)(permanence*localityBias));
//      }
//    }*/
  }

  if(!HARDCODE_SPATIAL)
    region->inhibitionRadius = averageReceptiveFieldSize(region);
  else
    region->inhibitionRadius = 0;

  /*desiredLocalActivity A parameter controlling the number of columns that will be*/
  float dla = 0;
  if(region->localityRadius==0)
    dla = region->inhibitionRadius * region->pctLocalActivity;
  else
    dla = (region->localityRadius*region->localityRadius) * region->pctLocalActivity;
  region->desiredLocalActivity = max(2, round(dla));

  if(DEBUG) {
    printf("\nRegion Created (C++)");
    printf("\ncolumnGrid = (%d, %d)", colGridSizeX, colGridSizeY);
    printf("\nxSpace, ySpace = %f %f", region->xSpace, region->ySpace);
    printf("\ninputRadius = %d", inputRadius);
    printf("\ndesiredLocalActivity = %d", region->desiredLocalActivity);
    printf("\nsynapsesPerProximalSegment = %d", synapsesPerSegment);
    printf("\nminOverlap = %g", region->minOverlap);
    printf("\nconPerm,permInc = %f %f\n", CONNECTED_PERM, PERMANENCE_INC);
    /*printf("outputGrid = ", outData.shape);*/
  }

  return region;
}

/**
 * Free the memory that has been allocated by fields within the Region
 * structure.  In this case, free the array of Columns that were
 * allocated (and recursively all the fields within the Column structs).
 * This function does NOT free the Region itself.
 */
void deleteRegion(Region* region) {
  int i;
  for(i=0; i<region->numCols; ++i)
    deleteColumn(&(region->columns[i]));
  free(region->columns);
  region->columns = NULL;
}

/**
 * Calculate both the activation accuracy and the prediction accuracy for all
 * the column cells in this region within the last processed time step.
 * The activation accuracy is the number of correctly predicted active columns
 * out of the total active columns.  The prediction accuracy is the number of
 * correctly predicted active columns out of the total sequence-segment
 * predicted columns (most recent time step).
 * @param result a float[2] (activationAcc, predictionAcc) that will contain
 * the float values (between 0.0-1.0) of the most recent region accuracy.
 */
void getLastAccuracy(Region* region, float* result) {
  /*want to know % active columns that were correctly predicted*/
  int sumP = 0;
  int sumA = 0;
  int sumAP = 0;
  int i,c,s;
  for(i=0; i<region->numCols; ++i) {
    Column* col = &(region->columns[i]);
    if(col->isActive)
      ++sumA;
    for(c=0; c<col->numCells; ++c) {
      Cell* cell = &(col->cells[c]);
      bool addP = false;
      if(cell->wasPredicted) {
        for(s=0; s<cell->numSegments; ++s) {
          Segment* seg = &(cell->segments[s]);
          if(seg->wasActive && seg->isSequence) {
            addP = true;
            break;
          }
        }
      }
      if(addP) {
        ++sumP;
        if(col->isActive)
          ++sumAP;
        break;
      }
    }
  }

  /*compare active columns now, to predicted columns from t-1*/
  float pctA = 0.0;
  float pctP = 0.0;
  if(sumA > 0)
    pctA = (float)sumAP / (float)sumA;
  if(sumP > 0)
    pctP = (float)sumAP / (float)sumP;
  result[0] = pctA;
  result[1] = pctP;
}

/**
 * Return the total number of segments in the Region that match the number of
 * predictionSteps. If pass in zero, return count of total segments regardless
 * of predictionSteps.
 */
int numRegionSegments(Region* region, int predictionSteps) {
  int c=0, i,j;
  for(i=0; i<region->numCols; ++i) {
    Column* col = &(region->columns[i]);
    for(j=0; j<col->numCells; ++j)
      c += numCellSegments(&col->cells[j], predictionSteps);
  }
  return c;
}

/**
 * def __kthScore(self, cols, k):
 *  """ Given the list of columns, return the k'th highest overlap value. """
 *  sorted = []
 *  for c in cols:
 *    sorted.append(c.overlap)
 *  sorted.sort()
 *  i = max(0, min(len(sorted)-1, len(sorted)-k))
 *  return sorted[i]
 */
float kthScore(Region* region, Column* col, int k) {
  /*first find bounds of neighbors within inhibitionRadius of 'col'*/
  int irad = round(region->inhibitionRadius);
  int x0 = max(0, min(col->cx-1, col->cx-irad));
  int y0 = max(0, min(col->cy-1, col->cy-irad));
  int x1 = min(region->width, max(col->cx+1, col->cx+irad));
  int y1 = min(region->height, max(col->cy+1, col->cy+irad));

  x1 = min(region->width, x1+1); /*extra 1's for correct looping*/
  y1 = min(region->height, y1+1);

  int x,y;
  for(x=x0; x<x1; ++x) {
    for(y=y0; y<y1; ++y) {
      /*cols.push_back(getColumn(x,y));*/
    }
  }

/*  TreeSet<Integer> overlaps = new TreeSet<Integer>();
//  for(Column col : cols)
//    overlaps.add(col.getOverlap());
//  int i = Math.max(0, overlaps.size()-k);
//  return (Integer)overlaps.toArray()[i];
  //get overlap values of each of the neighbor columns
  //return the kth largest.  need to sort, then return sorted[k]*/

  return 1.0;/*TODO implement kthScore for non-hardcoded spatial pooling*/
}

/**
 * Perform one time step of SpatialPooling for the current input in this Region.
 * The result will be a subset of Columns being set as active as well
 * as (proximal) synapses in all Columns having updated permanences and
 * boosts, and the Region will update inhibitionRadius.
 *
 * From the Numenta Docs:
 * Phase 1: compute the overlap with the current input for each column.
 * Given an input vector, the first phase calculates the overlap of each
 * column with that vector. The overlap for each column is simply the number
 * of connected synapses with active inputs, multiplied by its boost. If
 * this value is below minOverlap, we set the overlap score to zero.
 *
 * Phase 2: compute the winning columns after inhibition.
 * The second phase calculates which columns remain as winners after the
 * inhibition step. desiredLocalActivity is a parameter that controls the
 * number of columns that end up winning. For example, if desiredLocalActivity
 * is 10, a column will be a winner if its overlap score is greater than the
 * score of the 10'th highest column within its inhibition radius.
 *
 * Phase 3: update synapse permanence and internal variables.
 * The third phase performs learning; it updates the permanence values of all
 * synapses as necessary, as well as the boost and inhibition radius.
 *
 * The main learning rule is implemented in lines 20-26. For winning columns,
 * if a synapse is active, its permanence value is incremented, otherwise it
 * is decremented. Permanence values are constrained to be between 0 and 1.
 *
 * Lines 28-36 implement boosting. There are two separate boosting mechanisms
 * in place to help a column learn connections. If a column does not win often
 * enough (as measured by activeDutyCycle), its overall boost value is
 * increased (line 30-32). Alternatively, if a column's connected synapses
 * do not overlap well with any inputs often enough (as measured by
 * overlapDutyCycle), its permanence values are boosted (line 34-36).
 * Note: once learning is turned off, boost(c) is frozen.
 * Finally at the end of Phase 3 the inhibition radius is recomputed (line 38).
 */
void performSpatialPooling(Region* region) {
  int i;
  /*If hardcoded, we assume the input bits correspond directly to active columns*/
  if(HARDCODE_SPATIAL) {
    for(i=0; i<region->numCols; ++i)
      region->columns[i].isActive = region->inputData[i]==1;
    return;
  }

  /*Phase 1: Compute Column Input Overlaps*/
  for(i=0; i<region->numCols; ++i)
    computeOverlap(&(region->columns[i]));

  /*Phase 2: Compute Active Columns (Winners after inhibition)*/
  for(i=0; i<region->numCols; ++i) {
    Column* col = &(region->columns[i]);
    col->isActive = false;
    if(col->overlap > 0) {
      /*neighbors(neighborCols, col);*/
      float minLocalActivity = kthScore(region, col, region->desiredLocalActivity);
      if(col->overlap >= minLocalActivity)
        col->isActive = true;
    }
  }

  /*Phase 3: Synapse Boosting (Learning)*/
  if(region->spatialLearning) {
    for(i=0; i<region->numCols; ++i) {
      if(region->columns[i].isActive)
        updateColumnPermanences(&(region->columns[i]));
    }

    for(i=0; i<region->numCols; ++i)
      performBoosting(&(region->columns[i]));

    region->inhibitionRadius = averageReceptiveFieldSize(region);
  }
}

/**
 *  Populate the Column vector reference with all columns that are
 *  within inhibitionRadius of the specified input column.
 */
/*void neighbors(Region* region, Column* col) {
//  int irad = round(_inhibitionRadius);
//  int x0 = max(0, min(col->cx()-1, col->cx()-irad));
//  int y0 = max(0, min(col->cy()-1, col->cy()-irad));
//  int x1 = min(_width, max(col->cx()+1, col->cx()+irad));
//  int y1 = min(_height, max(col->cy()+1, col->cy()+irad));
//
//  x1 = min(_width, x1+1); //extra 1's for correct looping
//  y1 = min(_height, y1+1);
//
//  for(int x=x0; x<x1; ++x) {
//    for(int y=y0; y<y1; ++y)
//      cols.push_back(getColumn(x,y));
//  }
//}*/

/**
 * Perform one time step of Temporal Pooling for this Region.
 *
 * From the Numenta Docs:
 * The input to this code is activeColumns(t), as computed by the spatial pooler.
 * The code computes the active and predictive state for each cell at the
 * current timestep, t. The boolean OR of the active and predictive states
 * for each cell forms the output of the temporal pooler for the next level.
 *
 * Phase 1: compute the active state, activeState(t), for each cell.
 * The first phase calculates the activeState for each cell that is in a winning column.
 * For those columns, the code further selects one cell per column as the
 * learning cell (learnState). The logic is as follows: if the bottom-up
 * input was predicted by any cell (i.e. its predictiveState output was 1 due
 * to a sequence segment), then those cells become active (lines 23-27).
 * If that segment became active from cells chosen with learnState on, this
 * cell is selected as the learning cell (lines 28-30). If the bottom-up input
 * was not predicted, then all cells in the col become active (lines 32-34).
 * In addition, the best matching cell is chosen as the learning cell (lines 36-41)
 * and a new segment is added to that cell.
 *
 * Phase 2: compute the predicted state, predictiveState(t), for each cell.
 * The second phase calculates the predictive state for each cell. A cell will turn on
 * its predictive state output if one of its segments becomes active, i.e. if
 * enough of its lateral inputs are currently active due to feed-forward input.
 * In this case, the cell queues up the following changes: a) reinforcement of the
 * currently active segment (lines 47-48), and b) reinforcement of a segment that
 * could have predicted this activation, i.e. a segment that has a (potentially weak)
 * match to activity during the previous time step (lines 50-53).
 *
 * Phase 3: update synapses.
 * The third and last phase actually carries out learning. In this phase segment
 * updates that have been queued up are actually implemented once we get feed-forward
 * input and the cell is chosen as a learning cell (lines 56-57). Otherwise, if the
 * cell ever stops predicting for any reason, we negatively reinforce the segments
 * (lines 58-60).
 */
void performTemporalPooling(Region* region) {
  /*Phase 1: Compute cell active states and segment learning updates
  //18. for c in activeColumns(t)
  //19.
  //20.   buPredicted = false
  //21.   lcChosen = false
  //22.   for i = 0 to cellsPerColumn - 1
  //23.     if predictiveState(c, i, t-1) == true then
  //24.       s = getActiveSegment(c, i, t-1, activeState)
  //25.       if s.sequenceSegment == true then
  //26.         buPredicted = true
  //27.         activeState(c, i, t) = 1
  //28.         if segmentActive(s, t-1, learnState) then
  //29.           lcChosen = true
  //30.           learnState(c, i, t) = 1
  //31.
  //32.   if buPredicted == false then
  //33.     for i = 0 to cellsPerColumn - 1
  //34.       activeState(c, i, t) = 1
  //35.
  //36.   if lcChosen == false then
  //37.     i,s = getBestMatchingCell(c, t-1)
  //38.     learnState(c, i, t) = 1
  //39.     sUpdate = getSegmentActiveSynapses (c, i, s, t-1, true)
  //40.     sUpdate.sequenceSegment = true
  //41.     segmentUpdateList.add(sUpdate)*/
  int i,c,s;
  for(i=0; i<region->numCols; ++i) {
    Column* col = &(region->columns[i]);
    if(col->isActive) {
      bool buPredicted = false;
      bool learningCellChosen = false;
      for(c=0; c<col->numCells; ++c) {
        Cell* cell = &(col->cells[c]);
        if(cell->wasPredicted) {
          Segment* segment = getPreviousActiveSegment(cell);

          if(segment!=NULL && segment->isSequence) {
            buPredicted = true;
            cell->isActive = true;

            if(region->temporalLearning && wasSegmentActiveFromLearning(segment)) {
              learningCellChosen = true;
              cell->isLearning = true;
            }
          }
        }
      }

      if(!buPredicted) {
        for(c=0; c<col->numCells; ++c)
          col->cells[c].isActive = true;
      }

      if(region->temporalLearning && !learningCellChosen) {
        /*printf("bestSeg for (%d %d)\n", col->cx(), col->cy());*/
        Segment* bestSeg = NULL;
        Segment** bestSegPtr = &bestSeg;
        int bestSegID = -1;
        Cell* bestCell = getBestMatchingCell(col, bestSegPtr, &bestSegID, 1, true);
        bestCell->isLearning = true;

        bestSeg = *bestSegPtr;

        /*
         * 1) need to processSegment before step1
         * 2) need a processSynapse and store wasActive to fix
         *    since asking wasSynapseActive is using isSynapseConnected
         */

        /*segUpdate is added internally to Cell's update list*/
        SegmentUpdateInfo* segmentToUpdate =
            updateSegmentActiveSynapses(bestCell, true, bestSegID, true);
        segmentToUpdate->numPredictionSteps = 1;/*sequence segment*/

        /*#bestSeg may be partial-sort-of match, but it could dec-perm
        //#other syns from different step if cell overlaps...
        //
        //#try better minOverlap to prevent bad boosting?
        //#try to disable learning if predictions match heavily?
        //
        //#Do we need to enforce max segments per cell?*/
      }
    }
  }

  /*Phase2
  //42. for c, i in cells
  //43.   for s in segments(c, i)
  //44.     if segmentActive(s, t, activeState) then
  //45.       predictiveState(c, i, t) = 1
  //46.
  //47.       activeUpdate = getSegmentActiveSynapses (c, i, s, t, false)
  //48.       segmentUpdateList.add(activeUpdate)
  //49.
  //50.       predSegment = getBestMatchingSegment(c, i, t-1)
  //51.       predUpdate = getSegmentActiveSynapses(
  //52.                                   c, i, predSegment, t-1, true)
  //53.       segmentUpdateList.add(predUpdate)*/
  for(i=0; i<region->numCols; ++i) {
    for(c=0; c<region->columns[i].numCells; ++c) {
      Cell* cell = &(region->columns[i].cells[c]);

      /*process all segments on the cell to cache the activity for later*/
      for(s=0; s<cell->numSegments; ++s)
        processSegment(&(cell->segments[s]));

      for(s=0; s<cell->numSegments; ++s) {
        Segment* seg = &(cell->segments[s]);
        if(seg->isActive) {
          setCellPredicting(cell, true);

          /*a) reinforcement of the currently active segment*/
          if(region->temporalLearning) {
            /*add segment update to this cell
            //printf("updateSegment (%d,%d) is ",_columns[i].cx(), _columns[i].cy());*/
            updateSegmentActiveSynapses(cell, false, s, false);
          }
          break;
        }
      }

      /*b) reinforcement of a segment that could have predicted
      //   this activation, i.e. a segment that has a (potentially weak)
      //   match to activity during the previous time step (lines 50-53).*/
      if(region->temporalLearning && cell->isPredicting) {
        /*printf("predSegment is ");*/
        int predSegID = -1;
        Segment* predSegment = getBestMatchingPreviousSegment(cell, &predSegID);

        /*either update existing or add new segment for this cell considering
        //only segments matching the number of prediction steps of the
        //best currently active segment for this cell*/
        SegmentUpdateInfo* predSegUpdate =
            updateSegmentActiveSynapses(cell, true, predSegID, true);
        if(predSegment==NULL)
          predSegUpdate->numPredictionSteps = cell->predictionSteps+1;
      }
    }
  }

  /*Phase3
  //54. for c, i in cells
  //55.   if learnState(c, i, t) == 1 then
  //56.     adaptSegments (segmentUpdateList(c, i), true)
  //57.     segmentUpdateList(c, i).delete()
  //58.   else if predictiveState(c, i, t) == 0 and predictiveState(c, i, t-1)==1 then
  //59.     adaptSegments (segmentUpdateList(c,i), false)
  //60.     segmentUpdateList(c, i).delete()*/
  if(!region->temporalLearning)
    return;
  for(i=0; i<region->numCols; ++i) {
    for(c=0; c<region->columns[i].numCells; ++c) {
      Cell* cell = &(region->columns[i].cells[c]);
      if(cell->isLearning) {
        applyCellSegmentUpdates(cell, true);
      }
      else if(!cell->isPredicting && cell->wasPredicted) {
        applyCellSegmentUpdates(cell, false);
      }
    }
  }
}

/**
 * Run the Region through a single time step.  It is assumed the state of
 * the input data array has been populated prior to calling this function.
 */
void runOnce(Region* region) {
  /*  if(DEBUG && _iters==0) {
  //    start_time = microsec_clock::universal_time();
  //    std::cout << "Max Threads: " << boost::thread::hardware_concurrency() << "\n";
  //  }*/
  int i;
  for(i=0; i<region->numCols; ++i)
    nextColumnTimeStep(&(region->columns[i]));

  performSpatialPooling(region);
  performTemporalPooling(region);

  /*++_iters;
  //  if(DEBUG && _iters % 1000 == 0) {
  //    time_duration taken = microsec_clock::universal_time() - start_time;
  //    std::cout << "RegionC iters: " << _iters << " (" << taken << " seconds)\n";
  //    //printf("RegionC iters: %d (%d sec)\n", _iters);
  //    start_time = microsec_clock::universal_time();
  //  }*/
}
