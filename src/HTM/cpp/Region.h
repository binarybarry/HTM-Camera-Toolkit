/*
 * Region.h
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

#ifndef REGIONC_H_
#define REGIONC_H_

#include "Column.h"

extern bool TEMPORAL_LEARNING;

//Represent an entire region of HTM columns for the CLA.
class Region {
public:
  Region(int inputSizeX, int inputSizeY, int colGridSizeX, int colGridSizeY,
      float pctInputPerCol=0.05, float pctMinOverlap=0.1, int localityRadius=0,
      float pctLocalActivity=0.02, int cellsPerCol=1, int segActiveThreshold=3,
      int newSynapseCount=5);
  ~Region();

  void runOnce();
  void updateInput(int* inputData);
  void getOutput(); //TODO output data
  void getLastAccuracy(float* result);

  void neighbors(std::vector<Column*>& cols, Column* col);

  inline int getWidth() { return _width; }
  inline int getHeight() { return _height; }
  inline int getInputWidth() { return _inputWidth; }
  inline int getInputHeight() { return _inputHeight; }

  inline float getPctInputPerCol() { return _pctInputPerCol; }
  inline float getPctMinOverlap() { return _pctMinOverlap; }
  inline float getPctLocalActivity() { return _pctLocalActivity; }

  inline int getLocalityRadius() { return _localityRadius; }
  inline int getNewSynapseCount() { return _newSynapseCount; }
  inline int getCellsPerCol() { return _cellsPerCol; }

  inline int getSegActiveThreshold() { return _segActiveThreshold; }
  inline float getMinOverlap() { return _minOverlap; }
  inline float getInhibitionRadius() { return _inhibitionRadius; }

  inline void setSpatialLearning(bool learn) { _spatialLearning = learn; }
  inline void setTemporalLearning(bool learn) {
    _temporalLearning = learn; TEMPORAL_LEARNING = learn;
  }

  inline Column* getColumn(int x, int y) { return &_columns[(y*_height)+x]; }
  inline int max(int a, int b) { return a>b ? a : b; }
  inline int min(int a, int b) { return a<b ? a : b; }

protected:
  void performSpatialPooling();
  void performTemporalPooling();

  void performTemporalPoolingParallel();
  void performTemporalPhase1(Column* col);
  void performTemporalPhase2(Column* col);
  void performTemporalPhase3(Column* col);

  float kthScore(std::vector<Column*>& cols, int k);
  float averageReceptiveFieldSize();

private:
  int _inputWidth, _inputHeight;
  int _localityRadius;
  int _cellsPerCol;
  int _segActiveThreshold;
  int _newSynapseCount;

  float _pctInputPerCol;
  float _pctMinOverlap;
  float _pctLocalActivity;

  bool _spatialLearning;
  bool _temporalLearning;

  int _width, _height;
  float _xSpace, _ySpace;

  Column* _columns;
  int _numCols;

  float _minOverlap;
  float _inhibitionRadius;
  int _desiredLocalActivity;

  int* _inputData; //TODO: optimize for space with std::bitset?
  int _nInput;
  int _iters;
};

#endif /* REGIONC_H_ */

