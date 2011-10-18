/* File: htmc.i */
%module htmc

%{
#define SWIG_FILE_WITH_INIT
#include "Region.h"
#include "Column.h"
#include "AbstractCell.h"
#include "Cell.h"
#include "Segment.h"
#include "Synapse.h"
#include "SegmentUpdateInfo.h"
%}

%include "carrays.i"
%array_class(float, floatCArray);
%array_class(int, intCArray);

%include "Region.h"
%include "Column.h"
%include "AbstractCell.h"
%include "Cell.h"
%include "Segment.h"
%include "Synapse.h"
%include "SegmentUpdateInfo.h"
