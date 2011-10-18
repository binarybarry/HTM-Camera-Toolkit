/*
 * AbstractCell.h
 *
 *  Created on: Sep 28, 2011
 *      Author: barry
 *
 * AbstractCell is an interface used by HTM Region cells
 * that can represent either proximal (input) cells or distal
 * (temporal context) cells.
 */

#ifndef ABSTRACTCELL_H_
#define ABSTRACTCELL_H_

class AbstractCell {
public:
  virtual bool isActive() = 0;
  virtual bool wasActive() = 0;
  virtual bool wasLearning() = 0;
  virtual bool isDistal() { return false; }
};

#endif /* ABSTRACTCELL_H_ */
