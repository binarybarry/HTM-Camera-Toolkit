package htm;

/**
 * Represent a single input bit from an external source.
 * For an HTM this means an input bit used by a proximal segment.
 */
public class InputCell extends AbstractCell {

  private final int _x, _y, _index;
  private final byte[] _inputData;
  
  /**
   * Create a new InputCell connected to the value defined by
   * the index into the inputData array.  We assume the inputData
   * array changes its contents between time steps and the cell
   * is re-read for data changes.
   * @param index the index into the inputData array to read for activation.
   * @param inputData the inputData array to read for activation.
   */
  public InputCell(int x, int y, int index, byte[] inputData) {
    _x = x;
    _y = y;
    _index = index;
    _inputData = inputData;
  }

  @Override
  public boolean isActive() {
    return _inputData[_index]==1;
  }

  @Override
  public boolean wasActive() {
    return false;
  }

  @Override
  public boolean wasLearning() {
    return false;
  }

  @Override
  public int ix() {
    return _x;
  }

  @Override
  public int iy() {
    return _y;
  }

  @Override
  public int gridIndex() {
    return _index;
  }
}
