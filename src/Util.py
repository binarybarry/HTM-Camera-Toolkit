"""
Created on Feb 15, 2011

@author: Barry Maturkanich

Utility methods used by the rest of the package.
Only one so far, a helper to convert a PIL image into
a Wx image.
"""

from StringIO import StringIO

import wx

def convertToWxImage(image):
  """Convert the value (string or PIL image) to a wx image."""

  if type(image) is str:
    # Load from stream
    return wx.ImageFromStream(StringIO(image))

  else:
    # Convert from PIL
    if 'A' in image.mode:
      if image.mode != 'RGBA':
        image = image.convert('RGBA')
      wxImage = wx.EmptyImage(*image.size)
      wxImage.SetData(image.convert('RGB').tostring())
      wxImage.SetAlphaData(image.tostring()[3::4])
    else:
      if image.mode != 'RGB':
        image = image.convert('RGB')
      wxImage = wx.EmptyImage(*image.size)
      wxImage.SetData(image.tostring())
    return wxImage