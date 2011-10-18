/*
 * Region.cpp
 *
 *  Created on: Sep 22, 2011
 *      Author: barry
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
 */

#include <math.h>
#include <stdio.h>
#include <vector>
#include <boost/config.hpp>
#include <boost/date_time/posix_time/ptime.hpp>
#include <mapreduce.hpp>
#include "Region.h"

float RAD_BIAS_PEAK = 0.8; //input-bit radius bias peak for default proximal perms
float RAD_BIAS_STD_DEV = 0.25; //input-bit radius standard deviation bias
bool HARDCODE_SPATIAL = true; //if true, assume input bits are the active columns
bool DEBUG = true;
bool TEMPORAL_LEARNING = false;
extern float PERMANENCE_INC;
extern float CONNECTED_PERM;

/**
 *  Region Initialization (from Numenta docs):
 *  Prior to receiving any inputs, the region is initialized by computing a list of initial
 *  potential synapses for each column. This consists of a random set of inputs selected
 *  from the input space. Each input is represented by a synapse and assigned a random
 *  permanence value. The random permanence values are chosen with two criteria.
 *  First, the values are chosen to be in a small range around connectedPerm (the minimum
 *  permanence value at which a synapse is considered "connected"). This enables potential
 *  synapses to become connected (or disconnected) after a small number of training
 *  iterations. Second, each column has a natural center over the input region, and the
 *  permanence values have a bias towards this center (they have higher values near
 *  the center).
 *
 *  In addition to this I have added a concept of Locality Radius, which is an
 *  additional parameter to control how far away synapse connections can be made
 *  instead of allowing connections anywhere.  The reason for this is that in the
 *  case of video images I wanted to experiment with forcing each Column to only
 *  learn on a small section of the total input to more effectively learn lines or
 *  corners in a small section without being 'distracted' by learning larger patterns
 *  in the overall input space (which hopefully higher hierarchical Regions would
 *  handle more successfully).  Passing in 0 for locality radius will mean no restriction
 *  which will more closely follow the Numenta doc if desired.
 *
 *  @param inputSize: (x,y) size of input data matrix from the external source.
 *  @param colGridSize: (x,y) number of Columns to create to represent this Region.
 *  @param pctInputPerCol: Percent of input bits each Column has potential synapses for.
 *  @param pctMinOverlap: Minimum percent of column's synapses for column to be considered.
 *  @param localityRadius: Furthest number of columns away to allow distal synapses.
 *  @param pctLocalActivity: Approximate percent of Columns within locality radius to be
 *  winners after inhibition.
 *  @param cellsPerCol: Number of (temporal context) cells to use for each Column.
 *  @param segActiveThreshold: Number of active synapses to activate a segment.
 *  @param newSynapseCount: number of new distal synapses added if none activated during
 *  learning.
 */
Region::Region(int inputSizeX, int inputSizeY, int colGridSizeX, int colGridSizeY,
    float pctInputPerCol, float pctMinOverlap, int localityRadius,
    float pctLocalActivity, int cellsPerCol, int segActiveThreshold,
    int newSynapseCount) {
  printf("Constructing Region...\n");

  _inputWidth = inputSizeX;
  _inputHeight = inputSizeY;
  _nInput = _inputWidth * _inputHeight;
  _iters = 0;

  _localityRadius = localityRadius;
  _cellsPerCol = cellsPerCol;
  _segActiveThreshold = segActiveThreshold;
  _newSynapseCount = newSynapseCount;

  _pctInputPerCol = pctInputPerCol;
  _pctMinOverlap = pctMinOverlap;
  _pctLocalActivity = pctLocalActivity;

  _spatialLearning = false;
  _temporalLearning = false;

  //Reduce the number of columns and map centers of input x,y correctly.
  //column grid will be relative to size of input grid in both dimensions
  _width = colGridSizeX;
  _height = colGridSizeY;
  _numCols = _width*_height;
  _xSpace = (_inputWidth-1*1.0) / fmaxf(1.0,(_width-1));
  _ySpace = (_inputHeight-1*1.0) / fmaxf(1.0,(_height-1));

  //Create the columns based on the size of the input data to connect to.
  _columns = new Column[_width*_height];
  for(int cx=0; cx<_width; ++cx) {
    for(int cy=0; cy<_height; ++cy) {
      int srcPosX = roundf(cx*_xSpace);
      int srcPosY = roundf(cy*_ySpace);
      _columns[(cy*_height)+cx].init(this, srcPosX, srcPosY, cx, cy);
    }
  }

//    #size the output array as double grid for 4-cell, else just pad the first
//    #array dimension for 2 or 3 cell (and same size if just 1-cell)
//    if cellsPerCol==4:
//      outShape = (len(self.columnGrid)*2, len(self.columnGrid[0])*2)
//    else:
//      outShape = (len(self.columnGrid)*cellsPerCol, len(self.columnGrid[0]))
//    self.outData = numpy.zeros(outShape, dtype=numpy.uint8)

  //how far apart are 2 Columns in terms of input space; calc radius from that
  float inputRadiusf = _localityRadius*_xSpace;

  //Now connect all potentialSynapses for the Columns
  int synapsesPerSegment = 1;
  if(_localityRadius==0)
    synapsesPerSegment = (_inputWidth*_inputHeight) * pctInputPerCol;
  else
    synapsesPerSegment = (inputRadiusf*inputRadiusf) * pctInputPerCol;

  //The minimum number of inputs that must be active for a column to be
  //considered during the inhibition step.
  _minOverlap = synapsesPerSegment * pctMinOverlap;

  //int longerSide = max(_inputWidth, _inputHeight);
  //random.seed(42) #same connections each time for easier debugging

  int inputRadius = roundf(inputRadiusf);
  int minY = 0;
  int maxY = _inputHeight-1;
  int minX = 0;
  int maxX = _inputWidth-1;
  for(int i=0; i<_numCols; ++i) {
    if(HARDCODE_SPATIAL) //no proximal synpases for hardcoded case
      break;
    Column* col = &_columns[i];

    //restrict synapse connections if localityRadius is non-zero
    if(_localityRadius > 0) {
      minY = max(0, col->iy()-inputRadius);
      maxY = min(_inputHeight-1, col->iy()+inputRadius);
      minX = max(0, col->ix()-inputRadius);
      maxX = min(_inputWidth-1, col->ix()+inputRadius);
    }
    //ensure we sample unique input positions to connect synapses to
//    allPos = []
//    for y in xrange(minY,maxY+1):
//      for x in xrange(minX,maxX+1):
//        allPos.append((x,y))
//    for rx,ry in random.sample(allPos, synapsesPerSegment):
//      inputCell = InputCell(rx, ry, self.inputData)
//      permanence = random.gauss(Synapse.CONNECTED_PERM, Synapse.PERMANENCE_INC)
//      permanence = max(0.0, permanence) #ensure minimum of zero to clamp edge cases
//      distance = sqrt((col.ix-rx)**2 + (col.iy-ry)**2)
//      localityBias = (RAD_BIAS_PEAK/0.4)*exp((distance/(longerSide*RAD_BIAS_STD_DEV))**2/-2)
//      syn = Synapse(inputCell, permanence*localityBias)
//      col.proximalSegment.addSynapse(syn)
    //TODO
  }

  if(!HARDCODE_SPATIAL)
    _inhibitionRadius = averageReceptiveFieldSize();
  else
    _inhibitionRadius = 0;

  //desiredLocalActivity A parameter controlling the number of columns that will be
  float dla = 0;
  if(_localityRadius==0)
    dla = _inhibitionRadius * _pctLocalActivity;
  else
    dla = (_localityRadius*_localityRadius) * _pctLocalActivity;
  _desiredLocalActivity = max(2, round(dla));

  if(DEBUG) {
    printf("\nRegion Created (C++)");
    printf("\ncolumnGrid = (%d, %d)", colGridSizeX, colGridSizeY);
    printf("\nxSpace, ySpace = %f %f", _xSpace, _ySpace);
    printf("\ninputRadius = %d", inputRadius);
    printf("\ndesiredLocalActivity = %d", _desiredLocalActivity);
    printf("\nsynapsesPerProximalSegment = %d", synapsesPerSegment);
    printf("\nminOverlap = %g", _minOverlap);
    printf("\nconPerm,permInc = %f %f\n", CONNECTED_PERM, PERMANENCE_INC);
    //printf("outputGrid = ", outData.shape);
  }
}

Region::~Region() {
  delete[] _columns;
}

/**
 *  Run one time step iteration for this Region.  All cells will have their current
 *  (last run) state pushed back to be their new previous state and their new current
 *  state reset to no activity.  Then SpatialPooling following by TemporalPooling is
 *  performed for one time step.
 */
using namespace boost::posix_time;
ptime start_time;
void Region::runOnce() {
  if(DEBUG && _iters==0) {
    start_time = microsec_clock::universal_time();
    std::cout << "Max Threads: " << boost::thread::hardware_concurrency() << "\n";
  }

  for(int i=0; i<_numCols; ++i)
    _columns[i].nextTimeStep();

  performSpatialPooling();
  performTemporalPooling(); //performTemporalPoolingParallel();

  ++_iters;
  if(DEBUG && _iters % 1000 == 0) {
    time_duration taken = microsec_clock::universal_time() - start_time;
    std::cout << "RegionC iters: " << _iters << " (" << taken << " seconds)\n";
    //printf("RegionC iters: %d (%d sec)\n", _iters);
    start_time = microsec_clock::universal_time();
  }
}

/**
 *  Update the values of the inputData for this Region by assigning the
 *  _inputData variable to a pointer to a new input array of data.
 *  @param newInput: integer pointer to array of data to use for next
 *  Region time step. The inputData array must point to an array the same
 *  size as the original inputData (size appropriate for the Region).
 */
void Region::updateInput(int* inputData) {
  _inputData = inputData;
}

/**
 * def getOutput(self):
 *  """
 *  Determine the output bit-matrix of the most recently run time step
 *  for this Region.  The Region output is a 2d numpy array representing all
 *  Cells present in the Region.  Bits are set to 1 if a Cell is active or
 *  predicting, all other bits are 0.  The output data will be a 2d numpy
 *  array of dimensions based on both the size of the column gird for this
 *  Region and how many cells per column are present.  If 1 cell per column
 *  the output array is the same shape as the column grid.  For 2 or 3 cells
 *  per column the output array's first dimension is multiplied by the number
 *  of cells (i.e. if the column grid is 40x30, then 2 cells would result in
 *  80x30 output grid, and 3 cells would yield a 120x30).  For 4 cells the
    output grid is double the dimension of the column grid (40x30 becomes
    80x60 on output).
    @return a 2d numpy array of containing the Region's collective output
    (the shape will be based on column grid and cells per column).
    """
    if self.cellsPerCol < 4:
      for col in self.columns:
        for cell in col.cells:
          cx = (col.cx*self.cellsPerCol) + cell.index
          self.outData[cx][col.cy] = 0
          if cell.isActive or cell.isPredicting:
            self.outData[cx][col.cy] = 1
 *  else:
 *    for col in self.columns:
 *      for cell in col.cells:
 *        cx = (col.cx*2) + (cell.index%2)
 *        cy = (col.cy*2) + (cell.index/2)
 *        self.outData[cx][cy] = 0
 *        if cell.isActive or cell.isPredicting:
 *          self.outData[cx][cy] = 1
 *  return self.outData
 */
void Region::getOutput() {
  //TODO support Region outputs for C++ implementation
}

/**
 *  Calculate both the activation accuracy and the prediction accuracy for all
 *  the column cells in this region within the last processed time step.
 *  The activation accuracy is the number of correctly predicted active columns
 *  out of the total active columns.  The prediction accuracy is the number of
 *  correctly predicted active columns out of the total sequence-segment
 *  predicted columns (most recent time step).
 *  @param result a float[2] (activationAcc, predictionAcc) that will contain
 *  the float values (between 0.0-1.0) of the most recent region accuracy.
 */
void Region::getLastAccuracy(float* result) {
  //want to know % active columns that were correctly predicted
  int sumP = 0;
  int sumA = 0;
  int sumAP = 0;
  for(int i=0; i<_numCols; ++i) {
    Column* col = &_columns[i];
    if(col->isActive())
      ++sumA;
    for(int c=0; c<col->numCells(); ++c) {
      Cell* cell = col->getCell(c);
      bool addP = false;
      if(cell->wasPredicted()) {
        for(int s=0; s<cell->numSegments(); ++s) {
          Segment* seg = cell->getSegment(s);
          if(seg->wasActive() && seg->isSequence()) {
            addP = true;
            break;
          }
        }
      }
      if(addP) {
        ++sumP;
        if(col->isActive())
          ++sumAP;
        break;
      }
    }
  }

  //compare active columns now, to predicted columns from t-1
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
 *  Perform one time step of SpatialPooling for the current input in this Region.
 *  The result will be a subset of Columns being set as active as well
 *  as (proximal) synapses in all Columns having updated permanences and
 *  boosts, and the Region will update inhibitionRadius.
 *
 *  From the Numenta Docs:
 *  Phase 1: compute the overlap with the current input for each column.
 *  Given an input vector, the first phase calculates the overlap of each
 *  column with that vector. The overlap for each column is simply the number
 *  of connected synapses with active inputs, multiplied by its boost. If
 *  this value is below minOverlap, we set the overlap score to zero.
 *
 *  Phase 2: compute the winning columns after inhibition.
 *  The second phase calculates which columns remain as winners after the
 *  inhibition step. desiredLocalActivity is a parameter that controls the
 *  number of columns that end up winning. For example, if desiredLocalActivity
 *  is 10, a column will be a winner if its overlap score is greater than the
 *  score of the 10'th highest column within its inhibition radius.
 *
 *  Phase 3: update synapse permanence and internal variables.
 *  The third phase performs learning; it updates the permanence values of all
 *  synapses as necessary, as well as the boost and inhibition radius.
 *
 *  The main learning rule is implemented in lines 20-26. For winning columns,
 *  if a synapse is active, its permanence value is incremented, otherwise it
 *  is decremented. Permanence values are constrained to be between 0 and 1.
 *
 *  Lines 28-36 implement boosting. There are two separate boosting mechanisms
 *  in place to help a column learn connections. If a column does not win often
 *  enough (as measured by activeDutyCycle), its overall boost value is
 *  increased (line 30-32). Alternatively, if a column's connected synapses
 *  do not overlap well with any inputs often enough (as measured by
 *  overlapDutyCycle), its permanence values are boosted (line 34-36).
 *  Note: once learning is turned off, boost(c) is frozen.
 *  Finally at the end of Phase 3 the inhibition radius is recomputed (line 38).
 */
void Region::performSpatialPooling() {
  //If hardcoded, we assume the input bits correspond directly to active columns
  if(HARDCODE_SPATIAL) {
    for(int i=0; i<_numCols; ++i)
      _columns[i].setActive(_inputData[i]==1);
    return;
  }

  //Phase 1: Compute Column Input Overlaps
  for(int i=0; i<_numCols; ++i)
    _columns[i].computeOverlap();

  //Phase 2: Compute Active Columns (Winners after inhibition)
  std::vector<Column*> neighborCols;
  for(int i=0; i<_numCols; ++i) {
    Column* col = &_columns[i];
    col->setActive(false);
    if(col->getOverlap() > 0) {
      neighbors(neighborCols, col);
      float minLocalActivity = kthScore(neighborCols, _desiredLocalActivity);
      if(col->getOverlap() >= minLocalActivity)
        col->setActive(true);
    }
  }

  //Phase 3: Synapse Boosting (Learning)
  if(_spatialLearning) {
    for(int i=0; i<_numCols; ++i) {
      if(_columns[i].isActive())
        _columns[i].updatePermanences();
    }

    for(int i=0; i<_numCols; ++i)
      _columns[i].performBoosting();

    _inhibitionRadius = averageReceptiveFieldSize();
  }
}

/**
 *  Populate the Column vector reference with all columns that are
 *  within inhibitionRadius of the specified input column.
 */
void Region::neighbors(std::vector<Column*>& cols, Column* col) {
  int irad = round(_inhibitionRadius);
  int x0 = max(0, min(col->cx()-1, col->cx()-irad));
  int y0 = max(0, min(col->cy()-1, col->cy()-irad));
  int x1 = min(_width, max(col->cx()+1, col->cx()+irad));
  int y1 = min(_height, max(col->cy()+1, col->cy()+irad));

  x1 = min(_width, x1+1); //extra 1's for correct looping
  y1 = min(_height, y1+1);

  for(int x=x0; x<x1; ++x) {
    for(int y=y0; y<y1; ++y)
      cols.push_back(getColumn(x,y));
  }
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
float Region::kthScore(std::vector<Column*>& cols, int k) {
  return 1.0;//TODO implement kthScore for non-hardcoded spatial pooling
}

/**
 * def __averageReceptiveFieldSize(self):
 *  """
 *  The radius of the average connected receptive field size of all the columns.
 *  The connected receptive field size of a column includes only the connected
 *  synapses (those with permanence values >= connectedPerm). This is used to
 *  determine the extent of lateral inhibition between columns.
 *  @return the average connected receptive field size (in column grid space).
 *  """
 *  dists = []
 *  for col in self.columns:
 *    for syn in col.getConnectedSynapses():
 *      d = ((col.ix-syn.inputSource.ix)**2 + (col.iy-syn.inputSource.iy)**2)**0.5
 *      dists.append(d / self.xSpace)
 *  return sum(dists) / len(dists)
 */
float Region::averageReceptiveFieldSize() {
  return 5.0;//TODO implement averageReceptiveFieldSize for non-hardcoded spatial pooling
}

/**
 *  Perform one time step of Temporal Pooling for this Region.
 *
 *  From the Numenta Docs:
 *  The input to this code is activeColumns(t), as computed by the spatial pooler.
 *  The code computes the active and predictive state for each cell at the
 *  current timestep, t. The boolean OR of the active and predictive states
 *  for each cell forms the output of the temporal pooler for the next level.
 *
 *  Phase 1: compute the active state, activeState(t), for each cell.
 *  The first phase calculates the activeState for each cell that is in a winning column.
 *  For those columns, the code further selects one cell per column as the
 *  learning cell (learnState). The logic is as follows: if the bottom-up
 *  input was predicted by any cell (i.e. its predictiveState output was 1 due
 *  to a sequence segment), then those cells become active (lines 23-27).
 *  If that segment became active from cells chosen with learnState on, this
 *  cell is selected as the learning cell (lines 28-30). If the bottom-up input
 *  was not predicted, then all cells in the col become active (lines 32-34).
 *  In addition, the best matching cell is chosen as the learning cell (lines 36-41)
 *  and a new segment is added to that cell.
 *
 *  Phase 2: compute the predicted state, predictiveState(t), for each cell.
 *  The second phase calculates the predictive state for each cell. A cell will turn on
 *  its predictive state output if one of its segments becomes active, i.e. if
 *  enough of its lateral inputs are currently active due to feed-forward input.
 *  In this case, the cell queues up the following changes: a) reinforcement of the
 *  currently active segment (lines 47-48), and b) reinforcement of a segment that
 *  could have predicted this activation, i.e. a segment that has a (potentially weak)
 *  match to activity during the previous time step (lines 50-53).
 *
 *  Phase 3: update synapses.
 *  The third and last phase actually carries out learning. In this phase segment
 *  updates that have been queued up are actually implemented once we get feed-forward
 *  input and the cell is chosen as a learning cell (lines 56-57). Otherwise, if the
 *  cell ever stops predicting for any reason, we negatively reinforce the segments
 *  (lines 58-60).
 */
void Region::performTemporalPooling() {
  //Phase 1: Compute cell active states and segment learning updates
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
  //41.     segmentUpdateList.add(sUpdate)
  for(int i=0; i<_numCols; ++i) {
    Column* col = &_columns[i];
    if(col->isActive()) {
      bool buPredicted = false;
      bool learningCellChosen = false;
      for(int c=0; c<col->numCells(); ++c) {
        Cell* cell = col->getCell(c);
        if(cell->wasPredicted()) {
          Segment* segment = cell->getPreviousActiveSegment();

          if(segment!=NULL && segment->isSequence()) {
            buPredicted = true;
            cell->setActive(true);

            if(_temporalLearning && segment->wasActiveFromLearning()) {
              learningCellChosen = true;
              cell->setLearning(true);
            }
          }
        }
      }

      if(!buPredicted) {
        for(int c=0; c<col->numCells(); ++c)
          col->getCell(c)->setActive(true);
      }

      if(_temporalLearning && !learningCellChosen) {
        //printf("bestSeg for (%d %d)\n", col->cx(), col->cy());
        Segment** bestSeg = NULL;
        Cell* bestCell = col->getBestMatchingCell(bestSeg, true, true);
        bestCell->setLearning(true);

        if(bestSeg==NULL)
          printf("bestSeg is NULL");

        //segUpdate is added internally to Cell's update list
        SegmentUpdateInfo* segmentToUpdate =
            bestCell->updateSegmentActiveSynapses(true, *bestSeg, true);
        segmentToUpdate->setSequence(true);

        //#bestSeg may be partial-sort-of match, but it could dec-perm
        //#other syns from different step if cell overlaps...
        //
        //#try better minOverlap to prevent bad boosting?
        //#try to disable learning if predictions match heavily?
        //
        //#Do we need to enforce max segments per cell?
      }
    }
  }
  //printf("Phase 2\n");

  //Phase2
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
  //53.       segmentUpdateList.add(predUpdate)
  for(int i=0; i<_numCols; ++i) {
    for(int c=0; c<_columns[i].numCells(); ++c) {
      Cell* cell = _columns[i].getCell(c);
      for(int s=0; s<cell->numSegments(); ++s) {
        Segment* seg = cell->getSegment(s);
        if(seg->isActive()) {
          cell->setPredicting(true);

          //a) reinforcement of the currently active segment
          if(_temporalLearning) {
            //add segment update to this cell
            //printf("updateSegment (%d,%d) is ",_columns[i].cx(), _columns[i].cy());
            cell->updateSegmentActiveSynapses(false, seg);
          }
          break;
        }
      }

      //b) reinforcement of a segment that could have predicted
      //   this activation, i.e. a segment that has a (potentially weak)
      //   match to activity during the previous time step (lines 50-53).
      if(_temporalLearning && cell->isPredicting()) {
        //printf("predSegment is ");
        Segment* predSegment = cell->getBestMatchingSegment(false, true);
        //printf("%d\n", predSegment);
        //TODO if predSegment is None, do we still add new? ok if same as above seg?
        //SegmentUpdateInfo* predSegUpdate =
        cell->updateSegmentActiveSynapses(true, predSegment, true);
      }
    }
  }

  //Phase3
  //54. for c, i in cells
  //55.   if learnState(c, i, t) == 1 then
  //56.     adaptSegments (segmentUpdateList(c, i), true)
  //57.     segmentUpdateList(c, i).delete()
  //58.   else if predictiveState(c, i, t) == 0 and predictiveState(c, i, t-1)==1 then
  //59.     adaptSegments (segmentUpdateList(c,i), false)
  //60.     segmentUpdateList(c, i).delete()
  if(!_temporalLearning)
    return;
  for(int i=0; i<_numCols; ++i) {
    for(int c=0; c<_columns[i].numCells(); ++c) {
      Cell* cell = _columns[i].getCell(c);
      if(cell->isLearning()) {
        cell->applySegmentUpdates(true);
      }
      else if(!cell->isPredicting() && cell->wasPredicted()) {
        cell->applySegmentUpdates(false);
      }
    }
  }
}


//////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////
//
// The following is an experimental implementation of the
// Temporal Pooling using MapReduce to compute each of the Columns
// in parallel rather than one at a time sequentially.  Since
// the calculation for each column is completely indepedant of
// all other columns we can quite easily break the task up such
// that several columns can be calculated in parallel.
//
// I use the C++ MapReduce library authored by Craig Henderson.
// Found at: http://www.craighenderson.co.uk/mapreduce/
//
// You will need this library as well as the Boost libraries
// in order to run the parallelized temporal pooler.
//
// The MapTask data source simply takes an array of all the
// columns and returns references to individual columns as each key.
//
// I then have a MapTask for each of the 3 Temporal Pooling pooling
// phases that work on a single column provided by the data source.
// In other words, we parallel-process Phase1 for all columns,
// then move on to Phase2 once all columns finish.  Same goes for
// Phase2 to Phase3.
//
// The ReduceTask is trivial as in our case we are modifying global
// data during the map tasks and as such we have nothing to reduce!
//
template<typename MapTask>
class ColumnSource : boost::noncopyable {
public:
  ColumnSource(Column* columns, int ncol) {
    _columns = columns;
    _ncol = ncol;
    reset();
  }

  void reset() { _icol = 0; }

  const bool setup_key(typename MapTask::key_type &key) {
    if(_icol >= _ncol)
      return false;
    key = _icol;
    _icol++;
    return true;
  }

  const bool get_data(typename MapTask::key_type &key,
                      typename MapTask::value_type &value) const {
    value = &_columns[key];
    return true;
  }

private:
  Column* _columns;
  int _ncol;
  int _icol;
};

struct Phase1MapTask : public mapreduce::map_task<int,Column*> {
  template<typename Runtime>
  void operator()(Runtime &runtime, key_type const &key,
      value_type const &value) const {
    //key = column array index integer
    //value= Column* pointer at that index
    Column* col = value;
    if(col->isActive()) {
       bool buPredicted = false;
       bool learningCellChosen = false;
       for(int c=0; c<col->numCells(); ++c) {
         Cell* cell = col->getCell(c);
         if(cell->wasPredicted()) {
           Segment* segment = cell->getPreviousActiveSegment();

           if(segment!=NULL && segment->isSequence()) {
             buPredicted = true;
             cell->setActive(true);

             if(TEMPORAL_LEARNING && segment->wasActiveFromLearning()) {
               learningCellChosen = true;
               cell->setLearning(true);
             }
           }
         }
       }

       if(!buPredicted) {
         for(int c=0; c<col->numCells(); ++c)
           col->getCell(c)->setActive(true);
       }

       if(TEMPORAL_LEARNING && !learningCellChosen) {
         //printf("bestSeg for (%d %d)\n", col->cx(), col->cy());
         Segment** bestSeg = NULL;
         Cell* bestCell = col->getBestMatchingCell(bestSeg, true, true);
         bestCell->setLearning(true);

         if(bestSeg==NULL)
           printf("bestSeg is NULL");

         //segUpdate is added internally to Cell's update list
         SegmentUpdateInfo* segmentToUpdate =
             bestCell->updateSegmentActiveSynapses(true, *bestSeg, true);
         segmentToUpdate->setSequence(true);

         //#bestSeg may be partial-sort-of match, but it could dec-perm
         //#other syns from different step if cell overlaps...
         //
         //#try better minOverlap to prevent bad boosting?
         //#try to disable learning if predictions match heavily?
         //
         //#Do we need to enforce max segments per cell?
       }
     }
    //runtime.emit_intermediate(key,value);
  }
};

struct Phase2MapTask : public mapreduce::map_task<int,Column*> {
  template<typename Runtime>
  void operator()(Runtime &runtime, key_type const &key,
      value_type const &value) const {
    //key = column array index integer
    //value= Column* pointer at that index
    Column* col = value;
    for(int c=0; c<col->numCells(); ++c) {
      Cell* cell = col->getCell(c);
      for(int s=0; s<cell->numSegments(); ++s) {
        Segment* seg = cell->getSegment(s);
        if(seg->isActive()) {
          cell->setPredicting(true);

          //a) reinforcement of the currently active segment
          if(TEMPORAL_LEARNING) {
            //add segment update to this cell
            //printf("updateSegment (%d,%d) is ",_columns[i].cx(), _columns[i].cy());
            cell->updateSegmentActiveSynapses(false, seg);
          }
          break;
        }
      }

      //b) reinforcement of a segment that could have predicted
      //   this activation, i.e. a segment that has a (potentially weak)
      //   match to activity during the previous time step (lines 50-53).
      if(TEMPORAL_LEARNING && cell->isPredicting()) {
        Segment* predSegment = cell->getBestMatchingSegment(false, true);
        //TODO if predSegment is None, do we still add new? ok if same as above seg?
        //SegmentUpdateInfo* predSegUpdate =
        cell->updateSegmentActiveSynapses(true, predSegment, true);
      }
    }
    //runtime.emit_intermediate(key,value);
  }
};

struct Phase3MapTask : public mapreduce::map_task<int,Column*> {
  template<typename Runtime>
  void operator()(Runtime &runtime, key_type const &key,
      value_type const &value) const {
    //key = column array index integer
    //value= Column* pointer at that index
    Column* col = value;
    for(int c=0; c<col->numCells(); ++c) {
      Cell* cell = col->getCell(c);
      if(cell->isLearning()) {
        cell->applySegmentUpdates(true);
      }
      else if(!cell->isPredicting() && cell->wasPredicted()) {
        cell->applySegmentUpdates(false);
      }
    }
    //runtime.emit_intermediate(key,value);
  }
};

struct PhaseReduceTask : public mapreduce::reduce_task<int,Column*> {
  template<typename Runtime, typename It>
  void operator()(Runtime &runtime, key_type const &key,
      It it, It ite) const {
    //runtime.emit(key, (*it));
  }
};

typedef mapreduce::job<Phase1MapTask, PhaseReduceTask,
                       mapreduce::null_combiner, ColumnSource<Phase1MapTask> > Phase1Job;
typedef mapreduce::job<Phase2MapTask, PhaseReduceTask,
                       mapreduce::null_combiner, ColumnSource<Phase1MapTask> > Phase2Job;
typedef mapreduce::job<Phase3MapTask, PhaseReduceTask,
                       mapreduce::null_combiner, ColumnSource<Phase1MapTask> > Phase3Job;

void Region::performTemporalPoolingParallel() {
  mapreduce::specification spec;
  spec.map_tasks    = 0;
  spec.reduce_tasks = std::max(1U, boost::thread::hardware_concurrency());

  ColumnSource<Phase1MapTask> colSrc(_columns, _numCols);
  mapreduce::results result;

  //printf("\nPhase 1\n");
  Phase1Job p1Job(colSrc, spec);
  p1Job.run<mapreduce::schedule_policy::cpu_parallel<Phase1Job> >(result);
  colSrc.reset();

  //printf("Phase 2\n");
  //Phase2
  Phase2Job p2Job(colSrc, spec);
  p2Job.run<mapreduce::schedule_policy::cpu_parallel<Phase2Job> >(result);
  colSrc.reset();

  //Phase3
  //self.recentUpdateMap.clear()
  if(!_temporalLearning)
    return;
  Phase3Job p3Job(colSrc, spec);
  p3Job.run<mapreduce::schedule_policy::cpu_parallel<Phase3Job> >(result);

}

