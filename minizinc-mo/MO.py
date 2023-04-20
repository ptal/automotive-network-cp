from ParetoFront import *

class MO:
  """Multi-objective solver maintining a Pareto front.
     See further information in the class `ParetoFront`.
  Args:
    instance (Instance): A constraint model.
    subsolver (Solver): A solver for the constraint model instance supporting `solve()` and `add_local_constraint()`."""
  def __init__(self, instance, subsolver):
    self.instance = instance
    self.subsolver = subsolver
    self.pareto_front = ParetoFront(instance)

  def solve(self):
    for x in self.subsolver.solve():
      self.pareto_front.join(x)
      print(x["objs"])
      print(self.pareto_front.to_str())
      print(self.pareto_front.front_constraint_mzn())
      yield x
      self.subsolver.add_local_constraint(self.pareto_front.front_constraint_mzn())

  def add_local_constraint(self, constraint):
    self.subsolver.add_local_constraint(constraint)

  def add_global_constraint(self, constraint):
    self.subsolver.add_global_constraint(constraint)
