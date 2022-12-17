from minizinc import Instance, Model, Result, Solver, Status
from typing import List

model = Model("../model/automotive-sat.mzn")
model.add_file("../data/dzn/topology50-14_001.dzn")
gecode = Solver.lookup("gecode")
instance = Instance(gecode, model)

class ParetoFront:
  front: List[List[int]] = []

  def push_sol(self, objs_str):
    objs = [int(obj) for obj in objs_str]
    # We keep a solution in the Pareto front if at least one of its objective is strictly higher than the corresponding one in the new solution.
    # In other terms, we keep all solutions that are not dominated by the new `objs`.
    self.front = list(filter(lambda f: any([obj[0] > obj[1] for obj in zip(objs, f)]), self.front))
    self.front.append(objs)

  def front_to_mzn(self):
    cons = "constraint ("
    for i in range(len(self.front)):
      f = self.front[i]
      cons += "("
      for j in range(len(f)):
        cons += f"objs[{j+1}] < {f[j]} "
        if j+1 != len(f):
          cons += "\\/ "
      cons += ")"
      if i+1 != len(self.front):
        cons += " /\\ "
    return cons + ");"

  def print(self):
    for s in self.front:
      print(s)

pareto_front: ParetoFront = ParetoFront()
res: Result = instance.solve(optimisation_level=3)
print(res.solution)
while res.status == Status.SATISFIED:
  with instance.branch() as child:
    pareto_front.push_sol(res['objs'])
    pareto_front.print()
    print(pareto_front.front_to_mzn())
    child.add_string(pareto_front.front_to_mzn())
    res = child.solve(optimisation_level=3)
    if res.solution is not None:
      print(res.solution)