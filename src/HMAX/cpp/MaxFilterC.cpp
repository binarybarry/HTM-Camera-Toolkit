/*
 * MaxFilterC.cpp
 *
 *  Created on: May 28, 2011
 *      Author: barry
 */

#include <math.h>
#include "MaxFilterC.h"

MaxFilterC::MaxFilterC(int sCount, int xyCount) {
  _sCount = sCount;
  _xyCount = xyCount;
}

MaxFilterC::~MaxFilterC() {
  //nothing to free
}

void MaxFilterC::computeLayer(LayerC* layerIn1, LayerC* layerIn2, LayerC* layerOut) {
  //It is tricky to pass LayerC** between python and C++ with Swig so I use this
  //uglier method of passing each layer as its own parameter for now...
  LayerC* layersIn[_sCount];
  layersIn[0] = layerIn1;
  layersIn[1] = layerIn2;

  int wo = layerOut->xSize();
  int ho = layerOut->ySize();

  float gmax=0.0f; //global max across all values in all layers
  int xc=0, yc=0;
  for(int f=0; f<layerOut->fSize(); ++f) {
    float* outData = layerOut->getLayerData(f);

    for(int y=0; y<ho; ++y) {
      yc = layerOut->yCenter(y);
      for(int x=0; x<wo; ++x) {
        xc = layerOut->xCenter(x);

        //Re-express xyCount as a distance in real-valued retinal coordinates.
        float xr = layersIn[0]->xSpace() * 0.5f * (float)_xyCount;
        float yr = layersIn[0]->ySpace() * 0.5f * (float)_xyCount;

        //For each input layer (each scale) perform a local max over position for feature F.
        float res = 0;
        for(int s=0; s<_sCount; s++) {
          int yi1, yi2, xi1, xi2;
          layersIn[s]->getXRFDist(xc, xr, xi1, xi2);
          layersIn[s]->getYRFDist(yc, yr, yi1, yi2);

          for(int xi=xi1; xi<=xi2; xi++) {
            for(int yi=yi1; yi<=yi2; yi++) {
              float v = layersIn[s]->getValue(xi, yi, f);
              res = fmaxf(res, v);
            }
          }
        }

        outData[(y*wo) + x] = res;
        gmax = fmaxf(res, gmax);
      }
    }
  }

  //use the global max to inhibit (zero-out) all values <20% of gmax
  float cutoff = gmax * 0.33;
  for(int f=0; f<layerOut->fSize(); ++f) {
    float* outData = layerOut->getLayerData(f);
    for(int y=0; y<ho; ++y) {
      for(int x=0; x<wo; ++x) {
        int i = (y*wo) + x;
        if(outData[i] < cutoff)
          outData[i] = 0.0f;
      }
    }
  }
}

