/*
 * GaborFilterC.cpp
 *
 *  Created on: May 25, 2011
 *      Author: barry
 */

#include <stdio.h>
#include <math.h>
#include "GaborFilterC.h"

GaborFilterC::GaborFilterC(float* thetas, int thetaCount, int size,
                           float lam, float sigma, float aspect) {
  const float pi = 3.1415927410125732f;

  _size = size;
  _thetaCount  = thetaCount;
  _gabors = new float[size*size * thetaCount];

  for(int f=0; f<thetaCount; f++) {
    float theta = thetas[f];
    //printf("\nTheta%d: %g", f, theta);

    // First we generate the filter.
    float sum   = 0.0f;
    float sumsq = 0.0f;

    int gi = f * size*size; //ptr = _gabors[f * size*size];

    for(int j=0; j<size; j++) {
      for(int i=0; i<size; i++) {
        float jj = 0.5f * (float)(1 - size) + (float)j;
        float ii = 0.5f * (float)(1 - size) + (float)i;

        float y = jj * sinf(theta) + ii * cosf(theta);
        float x = jj * cosf(theta) - ii * sinf(theta);

        float e;
        if(sqrtf(x*x + y*y) <= 0.5f * (float)size) {
          e = expf(-(x*x + aspect * aspect * y*y) / (2.0f * sigma*sigma));
          e = e * cosf(2.0f*pi * x / lam);
        }
        else {
          e = 0.0f;
        }

        _gabors[gi++] = e;

        sum   += e;
        sumsq += e * e;
      }
    }

    // Now we normalize it to have mean 0 and total energy (sum of squares) 1.
    float n = (float)(size*size);
    float mean = sum / n;
    float stdv = sqrtf(sumsq - sum * sum / n);

    gi = f * size*size;//ptr = _gabors[f * size*size];

    for(int j=0; j<size; j++) {
      for(int i=0; i<size; i++) {
        float e = _gabors[gi];
        _gabors[gi++] = (e - mean) / stdv;
      }
    }
  }

  //printf("\nInitialized GaborFilterC.\n");
}

/****************************************************************************************/

GaborFilterC::~GaborFilterC() {
  delete _gabors;
}

/****************************************************************************************/

void GaborFilterC::computeLayer(float* layerIn, int wi, int hi,
                                LayerC* layerOut) {
  for(int f=0; f<_thetaCount; ++f) {
    int gi0 = f * _size*_size;
    float* outData = layerOut->getLayerData(f);

    for(int y=0; y<layerOut->ySize(); ++y) {
      for(int x=0; x<layerOut->xSize(); ++x) {
        //Get the receptive field indicies of the input array
        float res = 0.0f;
        float len = 0.0f;
        int gi = gi0;

        for(int yi=y; yi<y+_size; ++yi) {
          for(int xi=x; xi<x+_size; ++xi) {
            float w = _gabors[gi++];
            float v = layerIn[(yi*wi) + xi];
            res += (w * v);
            len += (v * v);
          }
        }

        //Finally, the components of each
        //filter are normalized so that their mean is 0 and the sum of
        //their squares is 1
        res = fabsf(res);
        if(len > 0.0f) res /= sqrtf(len);

        outData[(y*layerOut->xSize()) + x] = res;
      }
    }
  }
}

void GaborFilterC::computeLayer(float* layerIn, int wi, int hi,
                                float* layerOut, int wo, int ho, int thetaIndex) {
  int gi0 = thetaIndex * _size*_size;
  for(int y=0; y<ho; ++y) {
    for(int x=0; x<wo; ++x) {
      //Get the receptive field indicies of the input array
      float res = 0.0f;
      //float len = 0.0f;
      //const float *ptr = _gabors[thetaIndex * _size*_size];
      int gi = gi0;

      for(int yi=y; yi<y+_size; ++yi) {
        for(int xi=x; xi<x+_size; ++xi) {
          float w = _gabors[gi++];
          float v = layerIn[(yi*wi) + xi];
          res += (w * v);
          //len += v * v;
        }
      }

      res = fabsf(res);
      //if (len > 0.0f) res /= sqrtf(len);
      layerOut[(y*wo) + x] = res;
    }
  }
}

