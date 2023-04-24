from datetime import datetime

class FilterWCTT:
  """Filter the Pareto front to the solutions accepted by the WCTT analysis."""
  def __init__(self, statistics, pareto_front, wctt):
    self.statistics = statistics
    self.pareto_front = pareto_front
    self.wctt = wctt
    FilterWCTT.init_statistics(self.statistics)

  def init_statistics(statistics):
    statistics["uf_time_sec"] = 0
    statistics["uf_calls"] = 0
    statistics["uf_solutions"] = 0
    statistics["uf_conflicts"] = 0
    statistics["hypervolume_before_uf"] = 0

  def _filter_wctt(self, res):
    self.statistics["uf_calls"] += 1
    time_start = datetime.now()
    conflict = self.wctt.analyse(res.solution)
    time_end = datetime.now()
    self.statistics["uf_time_sec"] += (time_end - time_start).total_seconds()
    if conflict == "true":
      self.statistics["uf_solutions"] += 1
      return True
    else:
      self.statistics["uf_conflicts"] += 1

  def solve(self):
    """Yield the solutions accepted by the WCTT analysis."""
    self.statistics["hypervolume_before_uf"] = self.pareto_front.hypervolume()
    for x in self.pareto_front.filter(self._filter_wctt):
      yield x

  def add_local_constraint(self, constraint):
    pass

  def add_global_constraint(self, constraint):
    pass
