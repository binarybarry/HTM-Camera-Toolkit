"""
HMAX is an algorithm inspired by circuits in the visual areas of 
the neocortex, mostly the feed-forward path through the ventral stream
which includes V1, V2, V4, and IT.

It only models the 'spatial pooling' aspects and does not account at all
for any time/temporal related abilities.  In the real brain temporal
processing is a central component and must be present to account for any
sort of real interaction, however HMAX lets us simplify one specific
processing aspect in the neocortical visual system to achieve a very 
limited yet very useful visual algorithm.  HMAX also serves as something
of a starting point for later building in temporal and/or top-down 
processing as we research over time.

HMAX uses scale-space and a spatial hierarchy to perform processing
on small sub-components of the image in multiple image scales/sizes.

To use, we need to create an HMAX object that takes:

1) a set of image dimensions/sizes where the largest size corresponds
   to the size of the native input images and all smaller sizes will
   be the native image scaled down.
2) 
"""

    