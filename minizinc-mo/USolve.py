from datetime import datetime

class USolve:
  """Filter the solutions produced by the underlying solver `subsolver` using an external function `ufo`.
  Args:
    instance (Instance): A constraint model.
    statistics (dict): A dictionary to store the statistics of the solver.
    subsolver (Solver): A solver for the constraint model instance.
    ufo (Solution -> String): An external function filtering the solutions produced by `subsolver`.
      It returns `true` if the solution is accepted, and a string describing the conflict otherwise.
      The conflict must be over-approximating, meaning it does not remove any further solution from the problem, but it must removes the current non-accepted one.
      The solution is yield only if the function returns `true`."""
  def __init__(self, instance, statistics, subsolver, ufo):
    self.instance = instance
    self.statistics = statistics
    self.subsolver = subsolver
    self.ufo = ufo
    self.local_constraints = []
    USolve.init_statistics(self.statistics)

  def init_statistics(statistics):
    """We add statistics about the uf function: uf_time_sec, uf_calls, uf_solutions, uf_conflicts, uf_solutions_list."""
    statistics["uf_time_sec"] = 0
    statistics["uf_calls"] = 0
    statistics["uf_solutions"] = 0
    statistics["uf_conflicts"] = 0
    statistics["uf_solutions_list"] = []

  def solve(self):
    self._subadd_local_constaints()
    for x in self.subsolver.solve():
      time_start = datetime.now()
      self.statistics["uf_calls"] += 1
      conflict = self.ufo(x)
      time_end = datetime.now()
      self.statistics["uf_time_sec"] += (time_end - time_start).total_seconds()
      if conflict == "true":
        self.statistics["uf_solutions_list"].append(True)
        self.statistics["uf_solutions"] += 1
        self.local_constraints = []
        yield x
      else:
        self.statistics["uf_solutions_list"].append(False)
        self.statistics["uf_conflicts"] += 1
        self._subadd_local_constaints()
        self.add_global_constraint(conflict)

  def _subadd_local_constaints(self):
    for c in self.local_constraints:
      self.subsolver.add_local_constraint(c)

  def add_local_constraint(self, constraint):
    self.local_constraints.append(constraint)

  def add_global_constraint(self, constraint):
    self.subsolver.add_global_constraint(constraint)
