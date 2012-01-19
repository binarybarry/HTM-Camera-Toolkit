package htm;

import java.util.Random;
import java.util.Set;

/**
 * Utility methods used by the HTM classes.
 * @author barry
 */
public class Util {

  /**
   * Select a random subset of n elements from the input set and store them
   * in the output set.  The elements will be removed from the input set and
   * stored in the output set.  The method will clear the output set before
   * beginning the subsetting operation.
   * @param input the input set of elements (items will be removed).
   * @param output the set storing the resulting random subset of elements.
   * @param n the number of elements to randomly select from input.
   * @param rand a random variable to control reproducibility.
   */
  public static <T> void createRandomSubset(Set<T> input, Set<T> output, int n, 
      Random rand) {
    output.clear();
    for(int i=0; i<n; ++i) {
      int ri = rand.nextInt(input.size());
      int j=0;
      T randItem = null;
      for(T item : input) {
        if(j==ri) {
          randItem = item;
          break;
        }
        ++j;
      }
      
      output.add(randItem);
      input.remove(randItem);
    }
  }

}
