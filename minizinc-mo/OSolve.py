from minizinc import Status

class OSolve:
  """A constraint programming solver repeatedly solving a constraint model without modifying it.
     It is aimed to be used with other combinators that update the problem.
     Args:
       instance (Instance): A constraint model.
       timer (Optional[Timer]): A timer to retrieve the remaining time budget. `None` if unlimited time budget.
       cores (Optional[Int]): The number of cores to use. `None` for single-threaded solving.
       free_search (Optional[Bool]): Whether to use the free search of the underlying solver and ignore model search annotations.
       optimisation_level (Int): The optimisation level of the preprocessing step when converting MiniZinc to FlatZinc (from 1 to 5). Note that this is done before each call to `solve`.
  """

  def __init__(self, instance, statistics, timer=None, cores=None, free_search=False, optimisation_level=1):
    self.instance = instance
    self.local_constraints = ""
    self.cores = cores
    self.timer = timer
    self.free_search = free_search
    self.optimisation_level = optimisation_level
    self.statistics = statistics

  def solve(self):
    """Solve the constraint model described by `instance` with the local constraints and yield all solutions found.
       Between two consecutive calls to `solve`, the constraint model should be modified, otherwise the same solution might be returned.
       The local constraints are reset after each call to `solve`.
       Returns:
         Solution:
           A solution to `instance`."""
    while True:
      if self.timer == None:
        timeout = None
      else:
        timeout = self.timer.remaining_time_budget()
        if timeout <= 0:
          break
      with self.instance.branch() as child:
        child.add_string(self.local_constraints)
        self.local_constraints = ""
        res = self.instance.solve(
          optimisation_level = self.optimisation_level,
          all_solutions = 1,
          free_search = self.free_search,
          timeout = timeout,
          processes = self.cores)
      self.statistics.update(res)
      if res.status == Status.SATISFIED:
        yield res
      else:
        break

  def add_local_constraint(self, constraint):
    """Add a constraint to the model only for the next call to `solve`."""
    self.local_constraints += "\n" + self.local_constraints

  def add_global_constraint(self, constraint):
    """Add a constraint to the model persisting between calls to `solve`."""
    self.instance.add_string(constraint)
