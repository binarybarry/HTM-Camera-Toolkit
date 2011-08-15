/*
 * MaxFilterC.h
 *
 *  Created on: May 28, 2011
 *      Author: barry
 *
 * Implementation of the Max Filter (C1) used by the HMAX algorithm.
 * The Max Filter is designed to take as input a set of 2 layers
 * that were last processed with the S1 Gabor filter.
 *
 * The filter will simply examine all the Gabor results for a given
 * layer position and select the maximum Gabor response present across
 * the 2 layer size scales.  Thus we are condensing 2 size scales (2 layers)
 * into 1 by only keeping the stronger of the 2 Gabor responses for each
 * orientation.
 */

#ifndef MAXFILTERC_H_
#define MAXFILTERC_H_

#include "LayerC.h"

class MaxFilterC {
public:

  MaxFilterC(int sCount, int xyCount);
  ~MaxFilterC();

  void computeLayer(LayerC* layerIn1, LayerC* layerIn2, LayerC* layerOut);

private:
  int _sCount, _xyCount;

};

#endif /* MAXFILTERC_H_ */
