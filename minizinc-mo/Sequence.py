from datetime import datetime

class Sequence:
  """A sequence of constraint solvers called one after the other."""
  def __init__(self, subsolvers, ignore_timeout = False):
    self.subsolvers = subsolvers
    self.active_subsolver = self.subsolvers[0]
    self.ignore_timeout = ignore_timeout

  def solve(self):
    """Yields all solutions of each solver in turn."""
    for s in self.subsolvers:
      self.active_subsolver = s
      try:
        for x in s.solve():
          yield x
      except TimeoutError:
        if not self.ignore_timeout:
          raise

  def add_local_constraint(self, constraint):
    """Adds a local constraint to the solver currently active in `solve`."""
    self.active_subsolver.add_local_constraint(constraint)

  def add_global_constraint(self, constraint):
    """Adds a constraint to all solvers in the sequence."""
    for s in self.subsolvers:
      s.add_global_constraint(constraint)
