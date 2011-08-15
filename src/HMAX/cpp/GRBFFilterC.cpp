/*
 * GRBFFilter.cpp
 *
 *  Created on: Jul 31, 2011
 *      Author: barry
 */

#include <stdio.h>
#include <math.h>
#include "GRBFFilterC.h"

GRBFFilterC::GRBFFilterC(int xyCount, float sigma) {
  _xyCount = xyCount;
  _sigma = sigma;
}

GRBFFilterC::~GRBFFilterC() {
  //nothing to free
}

void GRBFFilterC::computeLayer(float* learnedW, float* learnedPF, int learnedCount,
    LayerC* layerIn, LayerC* layerOut) {

  int wo = layerOut->xSize();
  int ho = layerOut->ySize();

  float xc=0, yc=0;
  for(int f=0; f<layerOut->fSize(); ++f) {
    float* outData = layerOut->getLayerData(f);
    int fi = f * (_xyCount*_xyCount);

    for(int y=0; y<ho; ++y) {
      yc = layerOut->yCenter(y);
      for(int x=0; x<wo; ++x) {
        xc = layerOut->xCenter(x);

        int yi1, yi2, xi1, xi2;
        layerIn->getXRFNear(xc, _xyCount, xi1, xi2);
        layerIn->getYRFNear(yc, _xyCount, yi1, yi2);

        //    """
        //    Calculate the Radial-Basis-Function distance between the learned
        //    template patch at index f to the patch from layerIn at layer position
        //    lpos and of the specified patch size
        //    """
        //    (xi1,xi2), xOK = layerInput.getXRFNear(cx, size)
        //    (yi1,yi2), yOK = layerInput.getYRFNear(cy, size)
        //
        //    #Now apply template F to the receptive field.
        //    xi1, yi1 = lpos
        //    res = 0.0
        //    for xi in xrange(xi1,xi1+size):
        //      for yi in xrange(yi1,yi1+size):
        //        w,pf = self.learned[f][xi-xi1][yi-yi1]
        //        v = layerIn.get((xi,yi), pf)
        //        diff = v-w
        //        res -= diff**2
        //
        //    #RBF will return between 1.0 and 0.0 where 1 is perfect match and
        //    #0 is very far away; with gaussian curve in-between the 2
        //    xyRatio = size / self.xyCountMin
        //    return numpy.exp(res / (2.0 * self.sigma**2 - xyRatio**2))
        int xii, yii;
        float w, pf, v, diff;
        float res = 0.0f;
        for(int xi=xi1; xi<xi1+_xyCount; ++xi) {
          xii = xi-xi1;
          for(int yi=yi1; yi<yi1+_xyCount; ++yi) {
            yii =  yi-yi1;
            w = learnedW[fi + ((yii*_xyCount) + xii)];
            pf = learnedPF[fi + ((yii*_xyCount) + xii)];
            v = layerIn->getValue(xi, yi, pf);
            diff = v-w;
            res -= (diff*diff);
          }
        }

        //float xyRatio = 1.0f; //_xyCount / _xyCount
        float result = expf(res / (2.0 * (_sigma*_sigma) - 1.0));
        outData[(y*wo) + x] = result;
      }
    }
  }
}

