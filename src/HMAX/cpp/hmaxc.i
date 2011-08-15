/* File: hmaxc.i */
%module hmaxc

%{
#define SWIG_FILE_WITH_INIT
#include "LayerC.h"
#include "GaborFilterC.h"
#include "MaxFilterC.h"
#include "GRBFFilterC.h"
%}

%include "carrays.i"
%array_class(float, floatCArray);
%array_class(int, intCArray);

%include "LayerC.h"
%include "GaborFilterC.h"
%include "MaxFilterC.h"
%include "GRBFFilterC.h"
