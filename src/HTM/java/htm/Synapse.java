package htm;

/**
 * Synapse
 *  A data structure representing a synapse. Contains a permanence value and the
 *  source input index.  Also contains a 'location' in the input space that this
 *  synapse roughly represents.
 */
public class Synapse {
  
  private final AbstractCell _inputSource;
  private float _permanence;
  
  //Global parameters that apply to all Region instances
  public static final float CONNECTED_PERM = 0.2f;    //Synapses with permanences above this value are connected.
  public static final float INITIAL_PERMANENCE = 0.3f;//initial permanence for distal synapses
  public static final float PERMANENCE_INC = 0.015f;  //Amount permanences of synapses are incremented in learning.
  public static final float PERMANENCE_DEC = 0.005f;  //Amount permanences of synapses are decremented in learning.
  
  /**
   * @param inputSource: object providing source of the input to this synapse
   * (either a Column's Cell or a special InputCell.
   * @param permanence: the synapses's initial permanence value (0.0-1.0).
   */
  Synapse(AbstractCell inputSource, float permanence) {
    _inputSource = inputSource;
    _permanence = permanence==0.0 ? 
        INITIAL_PERMANENCE : (float)Math.min(1.0,permanence);
  }
  
  /**
   * Return true if this synpase is currently connected (its permanence is
   * higher than CONNECTED_PERM).
   */
  public boolean isConnected() { 
    return _permanence >= CONNECTED_PERM; 
  }
  
  /**
   * Return true if this Synapse is active due to the current input.
   * Only consider if active if this synapse is connected.
   */
  public boolean isActive() {
    return isActive(true);
  }

  /**
   * Return true if this Synapse is active due to the current input.
   * @param connectedOnly: only consider if active if this synapse is connected.
   */
  public boolean isActive(boolean connectedOnly) {
    return _inputSource.isActive() && (isConnected() || !connectedOnly);
  }

  /**
   * Return true if this Synapse was active due to the previous input at t-1.
   * Only consider if active if this synapse is connected.
   */
  public boolean wasActive() {
    return wasActive(true);
  }
  
  /**
   * Return true if this Synapse was active due to the previous input at t-1.
   * @param connectedOnly: only consider if active if this synapse is connected.
   */
  public boolean wasActive(boolean connectedOnly) {
    return _inputSource.wasActive() && (isConnected() || !connectedOnly);
  }

  /**
   *  Return true if this Synapse was active due to the input previously being
   *  in a learning state.
   */
  public boolean wasActiveFromLearning() {
    return wasActive() && _inputSource.wasLearning();
  }

  /**
   * Increases the permanence of this synapse.
   */
  public void increasePermanence() {
    increasePermanence(0.0f);
  }
  
  /**
   * Increases the permanence of this synapse.
   */
  public void increasePermanence(float amount) {
    if(amount==0.0)
      amount = PERMANENCE_INC;
    _permanence = (float)Math.min(1.0, _permanence+amount);
  }
  
  /**
   * Decreases the permanence of this synapse.
   */
  public void decreasePermanence() {
    decreasePermanence(0.0f);
  }

  /**
   * Decreases the permanence of this synapse.
   */
  public void decreasePermanence(float amount) {
    if(amount==0.0)
      amount = PERMANENCE_DEC;
    _permanence = (float)Math.max(0.0, _permanence-amount);
  }
  
  /**
   * Return the current permanence value representing the connection strength
   * of this synapse.  The permanence is always a value between 0 and 1 where
   * 0 means not connected at all and 1 means fully connected.
   */
  public float getPermanence() {
    return _permanence;
  }

  /**
   * Return a reference to this synapse's distal cell.  Important
   * that this method only be called on distal synapses.
   */
  public Cell getCell() {
    return (Cell)_inputSource;
  }
  
  /**
   * Return a reference to the input source for this synapse.  This is will be an
   * HTM Cell for distal synapses or an InputCell for proximal synapses.
   */
  public AbstractCell getInputSource() {
    return _inputSource;
  }
  
  /**
   * If this is a proximal synapse, return the ix (input space x coordinate)
   * of the column of the cell the synapse is connected to.
   */
  public int getCellIX() {
    return _inputSource.ix();
  }
  
  /**
   * If this is a proximal synapse, return the iy (input space y coordinate)
   * of the column of the cell the synapse is connected to.
   */
  public int getCellIY() {
    return _inputSource.iy();
  }
}
