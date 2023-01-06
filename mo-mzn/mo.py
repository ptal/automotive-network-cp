import shutil
from pathlib import Path
from minizinc import Instance, Model, Result, Solver, Status
from dataclasses import asdict
from typing import List
import subprocess
import sys
import csv
import os

input_mzn = "../model/automotive-sat.mzn"
objectives_dzn = "../model/objectives.dzn" # Just because parameters directly in the mzn files are not accessible through the Python API...
input_dzn = "../data/dzn/topology50-14_001.dzn"
solver_name = "gecode"
data_name = Path(input_dzn).stem

class ParetoFront:
  front: List[List[int]] = []
  minimize_objs: List[bool] = []

  def __init__(self, minimize_objs_str):
    self.minimize_objs = [bool(obj) for obj in minimize_objs_str]

  # Minimization (`minimize` is true): `true` if `obj1` is less or equal to `obj2`.
  # Maximization: `true` if `obj1` is greater or equal to `obj2`.
  def compare(self, obj1, obj2, minimize):
    if minimize:
      return obj1 <= obj2
    else:
      return obj1 >= obj2

  # `true` if `objs1` dominates or is equal to `objs2`.
  def dominates(self, objs1, objs2):
    return all([self.compare(obj1, obj2, m) for (obj1, obj2, m) in zip(objs1, objs2, self.minimize_objs)])

  def push_sol(self, new_objs_str):
    # By construction, `objs` cannot be dominated by any solutions in the Pareto front.
    new_objs = [int(obj) for obj in new_objs_str]
    # We keep a solution in the Pareto front if at least one of its objective is strictly higher than the corresponding one in the new solution.
    # In other terms, we keep all solutions that are not dominated by `new_objs`.
    self.front = list(filter(lambda objs: not self.dominates(new_objs, objs), self.front))
    self.front.append(new_objs)

  def objective_mzn(self, objs, i):
    if self.minimize_objs[i]:
      return f"objs[{i+1}] < {objs[i]}"
    else:
      return f"objs[{i+1}] > {objs[i]}"

  def front_to_mzn(self):
    cons = "constraint ("
    for i in range(len(self.front)):
      objs = self.front[i]
      cons += "("
      for j in range(len(objs)):
        cons += self.objective_mzn(objs, j)
        if j+1 != len(objs):
          cons += "\\/ "
      cons += ")"
      if i+1 != len(self.front):
        cons += " /\\ "
    return cons + ");"

  def print(self):
    for s in self.front:
      print(s)

def create_output_dzn(data_name, res):
  output_dzn = "tmp/" + data_name + ".dzn"
  shutil.copyfile(input_dzn, output_dzn)
  with open(output_dzn, 'a') as odzn:
    solution = asdict(res.solution)
    for k,v in solution.items():
      if(isinstance(v, list)):
        odzn.write(k + "=" + str(v) + ";\n")
  return output_dzn

def create_output_topology(output_dzn, data_name):
  raw_csv = "../data/raw-csv/" + data_name + ".csv"
  output_topology = "tmp/" + data_name + ".csv"
  output = subprocess.run(["../dzn2topology", raw_csv, output_dzn], text=True, capture_output=True)
  if output.returncode == 0:
    with open(output_topology, 'w') as otopo:
      otopo.write(output.stdout)
  else:
    sys.exit("Error converting the DZN file " + output_dzn + " to a topology.\nstderr:\n" + output.stderr)
  return output_topology

def create_wctt_analysis(output_topology, data_name):
  output = subprocess.run(["java", "-jar", "../pegase-timing-analysis.jar", "tmp/"])
  if output.returncode == 0:
    return "timing-analysis-results/" + data_name + "_WCTT.csv"
  else:
    sys.exit("Error analyzing the topology file " + output_dzn + ".\nstderr:\n" + output.stderr)

# If it is unschedulable, we force the charge of at least one link to be less than its current charge.
def create_conflict(res):
  disjunction = []
  for i in range(len(res["charge"])):
    c = res["charge"][i]
    disjunction += f"charge[{i+1}] < {c}"
  return ' \\/ '.join(disjunction)

def analyse_wctt_result(output_analysis, res):
  with open(output_analysis, 'r') as fanalysis:
    for _ in range(5):
      next(fanalysis)
    wctt = csv.DictReader(fanalysis, delimiter=';')
    for row in wctt:
      # if the column slack is empty, it means the frame is scheduled using a best-effort strategy so no hard deadline.
      if row["Slack(ms)"] != '' and float(row["Slack(ms)"]) < 0:
        return create_conflict(res)
    return "false"

def underappx_analysis(res):
  output_dzn = create_output_dzn(data_name, res)
  output_topology = create_output_topology(output_dzn, data_name)
  output_analysis = create_wctt_analysis(output_topology, data_name)
  return analyse_wctt_result(output_analysis, res)

def initialize_directory():
  try:
    os.mkdir("tmp")
  except OSError as error:
    return

def usolve_mo(instance, model):
  pareto_front: ParetoFront = ParetoFront(instance['minimize_objs'])
  res: Result = instance.solve(optimisation_level=3)
  print(res.solution)
  while res.status == Status.SATISFIED:
    with instance.branch() as child:
      conflict = underappx_analysis(res)
      if conflict == "false":
        pareto_front.push_sol(res['objs'])
        pareto_front.print()
        print(pareto_front.front_to_mzn())
        child.add_string(pareto_front.front_to_mzn())
      else:
        print("Found conflict: " + conflict)
        child.add_string("constraint " + conflict + ";")
      res = child.solve(optimisation_level=3)
      if res.solution is not None:
        print(res.solution)


initialize_directory()
model = Model(input_mzn)
model.add_file(input_dzn, parse_data=True)
model.add_file(objectives_dzn, parse_data=True)
solver = Solver.lookup(solver_name)
instance = Instance(solver, model)
usolve_mo(instance, model)
