/*
 * LayerC.cpp
 *
 *  Created on: May 28, 2011
 *      Author: barry
 */

#include <math.h>
#include "LayerC.h"

LayerC::LayerC(int xSize, int ySize, int fSize, float xStart, float yStart,
    float xSpace, float ySpace, float* data) {
  _xSize = xSize;
  _ySize = ySize;
  _fSize = fSize;
  _xStart = xStart;
  _yStart = yStart;
  _xSpace = xSpace;
  _ySpace = ySpace;
  _data = data;
}

LayerC::~LayerC() {
  //nothing to free
}

int LayerC::xSize() {
  return _xSize;
}

int LayerC::ySize() {
  return _ySize;
}

int LayerC::fSize() {
  return _fSize;
}

float LayerC::xSpace() {
  return _xSpace;
}

float LayerC::ySpace() {
  return _ySpace;
}

float LayerC::getValue(int x, int y, int f) {
  return _data[(f*_xSize*_ySize) + (y*_xSize) + x];
}

void LayerC::setValue(int x, int y, int f, float val) {
  _data[(f*_xSize*_ySize) + (y*_xSize) + x] = val;
}

/**
 * Convert the input layer-space integer x-coordinate into its
 * equivalent in real-valued retinal space.  Since a layer space
 * coordinate represents a cell in retinal-space, the returned
 * value will represent the center point of that cell.
 * @param xi: integer x-coordinate in layer-space.
 * @return: equivalent real-valued x-coordinate in retinal-space.
 */
float LayerC::xCenter(int xi) {
  return _xStart + (xi*_xSpace);
}

/**
 * Convert the input layer-space integer y-coordinate into its
 * equivalent in real-valued retinal space.  Since a layer space
 * coordinate represents a cell in retinal-space, the returned
 * value will represent the center point of that cell.
 * @param xi: integer y-coordinate in layer-space.
 * @return: equivalent real-valued y-coordinate in retinal-space.
 */
float LayerC::yCenter(int yi) {
  return _yStart + (yi*_ySpace);
}

//    """
//    Similar to getXRFNear above, except instead of finding the N nearest
//    indices, we find all indices within distance R of C, both specified
//    in real-value retinal coordinates.  If any of the indices found are
//    invalid, the range in I1/I2 is truncated and the return value will
//    be false, otherwise we return true.
//    """
bool LayerC::getXRFDist(float c, float r, int &i1, int &i2) {
  int j1, j2;
  RFDist(_xSize, _xStart, _xSpace, c, r, i1, i2, j1, j2);

  return (i1 == j1) && (i2 == j2);
}

bool LayerC::getYRFDist(float c, float r, int &i1, int &i2) {
  int j1, j2;
  RFDist(_ySize, _yStart, _ySpace, c, r, i1, i2, j1, j2);

  return (i1 == j1) && (i2 == j2);
}

void LayerC::RFDist(int t, float s, float d, float c, float r,
                    int &i1, int &i2, int &j1, int &j2) {
  float dd = 1.0f / d;
  j1 = (int)ceilf ((c - r - s) * dd - 0.001f);
  j2 = (int)floorf((c + r - s) * dd + 0.001f);
  i1 = min(max(j1,  0), t    );
  i2 = min(max(j2, -1), t - 1);
}

float* LayerC::getLayerData(int f) {
  float* data = &_data[f * (_xSize*_ySize)];
  return data;
}

//    """
//    For the X dimension, find the N nearest indices to position C in the
//    real-valued retinal coordinate system.  The range of indices will be
//    returned in I1 and I2.  If any of the found indices are outside the valid
//    range [0 YSIZE-1] or [0 XSIZE-1], only the valid part of the range will
//    be returned in I1 and I2, and the function's return value will be false.
//    If N valid indices can be returned, the return value will be true.
//    """
bool LayerC::getXRFNear(float c, int n, int &i1, int &i2) {
  int j1, j2;
  RFNear(_xSize, _xStart, _xSpace, c, n, i1, i2, j1, j2);
  return (i1 == j1) && (i2 == j2);
}

bool LayerC::getYRFNear(float c, int n, int &i1, int &i2) {
  int j1, j2;
  RFNear(_ySize, _yStart, _ySpace, c, n, i1, i2, j1, j2);
  return (i1 == j1) && (i2 == j2);
}

void LayerC::RFNear(int t, float s, float d, float c, int n,
                    int &i1, int &i2, int &j1, int &j2) {
  float dd = 1.0f / d;
  j1 = (int)ceilf((c - s) * dd - 0.5 * n - 0.001);
  j2 = j1 + n - 1;
  i1 = min(max(j1, 0), t);
  i2 = min(max(j2,-1), t-1);
}
