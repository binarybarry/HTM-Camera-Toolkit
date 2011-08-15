"""
Created on May 3, 2011

@author: Barry Maturkanich

HMAX is an algorithm inspired by circuits in the visual areas of 
the neocortex, mostly the feed-forward path through the ventral stream
which includes V1, V2, V4, and IT.

The goal then is to be able to take an input image and decide which of
several classes of objects are present in the image.  Or at least be
able to say how closely an input image matches previously learned
example images.

HMAX only models the 'spatial pooling' aspects and does not account at all
for any time/temporal related abilities.  In the real brain temporal
processing is a central component and must be present to account for any
sort of real interaction, however HMAX lets us simplify one specific
processing aspect in the neocortical visual system to achieve a very 
limited yet very useful visual algorithm.  HMAX also serves as something
of a starting point for later building in temporal and/or top-down 
processing as we research over time.

HMAX uses scale-space and a spatial hierarchy to perform processing
on small sub-components of the image in multiple image scales/sizes.

The hierarchy consists of multiple Levels, with lower levels feeding
data into the higher levels, one level to the next.  The bottom-most
level takes in the original input image while the top-most level
performs the final classification decision.

Each level will consist of one or more Layers.  Each layer is intended
to handle differently scaled sizes of the original input image in order
to perform a sort of parallel processing of multiple object sizes.
As we ascend the hierarchy we slowly combine the scale layers by 
selecting the best responses between 2 neighboring scales resulting 
in an overall best response across many sizes.  This gives an increased
invarience to size when performing classification.

The HMAX algorithm used in this code is primarily based on the 
following academic paper: 
Jim Mutch and David G. Lowe.
Object class recognition and localization using sparse features 
with limited receptive fields. 2008.


In the actual application:
The NetworkFrame contains all the top-level UI to allow users to
define HMAX Networks and then visualize the states of each of its
layers to understand what the Network is coming up with and why.

The HMAX Network is trained using static images however the UI is
set up to allow playing video files and presenting each individual
video frame to the network.

Once you click to create an HMAX Network the first step is to perform
learning for the S2 level.  This level is interested in learned small
4x4 "patches" of cells within its layers.  By the time data gets to S2
it has been approximated as lines of various orientations.  S2 then
learns a set of these line-orientation patches.  Layer S2 will try
to then later describe entire images in terms of these learned patches.

Once S2 is trained, we then need to train C2 which ultimately is an SVM
(Support Vector Machine).  C2 looks at how closely all parts of the 
input image match each of the learned S2 patches.  It then passes these
results to its SVM along with a class label (which is toggled in the UI 
during training).

Once C2 is trained, we can perform inference on new images.  C2 will use
its trained SVM to estimate which class of image the input image is
most closely associated with.
"""
DEBUG = False #set to True to enable Debug print outs
    