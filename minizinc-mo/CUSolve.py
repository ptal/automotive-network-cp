from datetime import datetime

class CUSolve:
  """Similar to `USolve` but do not require the external function to produce over-approximating conflicts.
     The resulting solver is still over-approximating thanks to the usage of backtracking within this combinator.
  Args:
    instance (Instance): A constraint model.
    statistics (dict): A dictionary to store the statistics of the solver.
    subsolver (Solver): A solver for the constraint model instance.
    uf (Solution -> String): An external function filtering the solutions produced by `subsolver`.
      It returns `true` if the solution is accepted, and a string describing the conflict otherwise.
      When it returns a conflict `c`, it must at least implies the logical negation of the assignment so we do not return to the same solution again.
      The solution is yield only if the function returns `true`.
    oc (Solution -> String): A function creating an over-approximating conflict from the solution.
      It is necessary when exploring the complement of the state space created by `uf` so we do not return to the same solution.
      A simple and generic over-approximating conflict is the negation of the assignment."""
  def __init__(self, instance, statistics, subsolver, uf, oc):
    self.instance = instance
    self.statistics = statistics
    self.subsolver = subsolver
    self.uf = uf
    self.oc = oc
    self.conflicts = []
    self.local_constraints = []
    CUSolve.init_statistics(self.statistics)

  def init_statistics(statistics):
    """We add statistics about the uf function: uf_time_sec, uf_calls, uf_solutions, uf_conflicts, uf_conflicts_backtrack, uf_solutions_list."""
    statistics["uf_time_sec"] = 0
    statistics["uf_calls"] = 0
    statistics["uf_solutions"] = 0
    statistics["uf_conflicts"] = 0
    statistics["uf_conflicts_backtrack"] = 0
    statistics["uf_solutions_list"] = []

  def solve(self):
    while True:
      self._subadd_local_constraint()
      self._add_conflict_constraints()
      for x in self.subsolver.solve():
        time_start = datetime.now()
        self.statistics["uf_calls"] += 1
        conflict = self.uf(x)
        time_end = datetime.now()
        self.statistics["uf_time_sec"] += (time_end - time_start).total_seconds()
        # If we found a solution w.r.t. uf, we clean the local constraints and yield it.
        if conflict == "true":
          self.statistics["uf_solutions_list"].append(True)
          self.statistics["uf_solutions"] += 1
          self.local_constraints = []
          yield x
        else:
          self.statistics["uf_solutions_list"].append(False)
          self.statistics["uf_conflicts"] += 1
          self._push_conflict(x, conflict)
        self._subadd_local_constraint()
        self._add_conflict_constraints()
      # The loop exits when the subsolver has no more solution, in which case we backtrack the conflicts stack.
      self.statistics["uf_conflicts_backtrack"] += 1
      self._backtrack()
      if self.conflicts == []:
        break

  def add_local_constraint(self, constraint):
    self.local_constraints.append(constraint)

  def add_global_constraint(self, constraint):
    self.subsolver.add_global_constraint(constraint)

  def _subadd_local_constraint(self):
    for c in self.local_constraints:
      self.subsolver.add_local_constraint(c)

  def _backtrack(self):
    if self.conflicts != []:
      if self.conflicts[-1][0] == False:
        self.conflicts.pop()
        self._backtrack()
      else:
        self.conflicts[-1][0] = False

  def _push_conflict(self, x, conflict):
    self.conflicts.append([True, conflict, self.oc(x)])

  def _add_conflict_constraints(self):
    for left, c, oc in self.conflicts:
      if left:
        self.subsolver.add_local_constraint(c)
      else:
        self.subsolver.add_local_constraint("(not " + c + ")")
        self.subsolver.add_local_constraint(oc)
