package htm;

/**
 * Represent an abstract HTM Cell.  An abstract cell can have activation
 * and learning state, however in the simplest terms an abstract cell
 * represents an input source for segments.  Since segments can be distal or
 * proximal we use this abstraction to refer to either of them at a base level.
 */
public abstract class AbstractCell {
  
  /**
   * Return true if this Cell is active (false if not).
   */
  public abstract boolean isActive();
  
  /**
   * Return true if this Cell was active in the previous time step.
   */
  public abstract boolean wasActive();
  
  /**
   * Return true if this Cell was in the learning state in the previous
   * time step.
   */
  public abstract boolean wasLearning();
  
  /**
   * Return the x-coordinate representing the location of this Cell.
   * Often if this Cell is used by a proximal segment we need to know the
   * Cell's location to identify connection radius for the Column.
   */
  public abstract int ix();
  
  /**
   * Return the y-coordinate representing the location of this Cell.
   * Often if this Cell is used by a proximal segment we need to know the
   * Cell's location to identify connection radius for the Column.
   */
  public abstract int iy();
  
  /**
   * Return the linear grid array index this Cell represents within its associated
   * input data array.  While the ix/iy methods define the Cell's location within
   * a 2d grid space, this method returns the index within the same data as viewed
   * as a normal flat 1d array.
   * @return the linear grid array index this Cell represents.
   */
  public abstract int gridIndex();
  
  /**
   * Return true if this Cell represents a Cell connected to distal segments
   * (as opposed to proximal segments connected to columns).
   */
  public boolean isDistal() { return false; }

}
