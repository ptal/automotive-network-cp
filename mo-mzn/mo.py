import shutil
from pathlib import Path
from minizinc import Instance, Model, Result, Solver, Status
from dataclasses import asdict
from typing import List, Tuple
import subprocess
import sys
import csv
import os
from datetime import datetime, timedelta
import traceback
import logging
import argparse

class Config:
  def __init__(self):
    parser = argparse.ArgumentParser(
                prog = 'Multi-objective constraint programming with WCTT',
                description = 'This program computes a Pareto front of the deployment problem on switch-based network.')
    parser.add_argument('instance_name')
    parser.add_argument('--model_mzn', required=True)
    parser.add_argument('--objectives_dzn', required=True)
    parser.add_argument('--dzn_dir', required=True)
    parser.add_argument('--topology_dir', required=True)
    parser.add_argument('--solver_name', required=True)
    parser.add_argument('--timeout_sec', required=True, type=int)
    parser.add_argument('--results_dir', required=True)
    parser.add_argument('--bin', required=True)
    args = parser.parse_args()
    self.data_name = args.instance_name
    self.input_mzn = args.model_mzn
    self.objectives_dzn = args.objectives_dzn  # Just because parameters directly in the mzn files are not accessible through the Python API...
    self.input_dzn = args.dzn_dir + "/" + self.data_name + ".dzn"
    print(self.input_dzn)
    self.input_topology = args.topology_dir + "/" + self.data_name + ".csv"
    self.solver_name = args.solver_name
    self.timeout_sec = args.timeout_sec
    self.results_dir = args.results_dir + "/results"
    self.all_results_dir = args.results_dir + "/all_results"
    self.bin_dir = args.bin
    self.start_time_solving = datetime.now()
    self.initialize_directory(self.all_results_dir)
    self.initialize_directory(self.results_dir)

  def initialize_directory(self, dir):
    try:
      os.mkdir(dir)
    except OSError as error:
      pass

  def make_solution_filename(self, sol_dir, sol_id):
    return sol_dir + "/" + self.data_name + "_" + str(sol_id)

  def output_dzn(self, sol_id):
    return self.make_solution_filename(self.all_results_dir, sol_id) + ".dzn"

  def output_topology(self, sol_id):
    return self.make_solution_filename(self.all_results_dir, sol_id) + ".csv"

  def output_clean_dzn(self, sol_id):
    return self.make_solution_filename(self.results_dir, sol_id) + ".dzn"

  def output_clean_topology(self, sol_id):
    return self.make_solution_filename(self.results_dir, sol_id) + ".csv"

  def wctt_analyser(self):
    return self.bin_dir + "/pegase-timing-analysis.jar"

  def dzn2topology(self):
    return self.bin_dir + "/dzn2topology"

  def wctt_analysis_name(self, sol_id):
    return self.data_name + "_" + str(sol_id) + "_WCTT"

  def wctt_analysis_filename(self, sol_id):
    return self.wctt_analysis_name(sol_id) + ".csv"

  def wctt_analysis_input_dir(self, sol_id):
    return self.all_results_dir + "/" + self.wctt_analysis_name(sol_id)

  def wctt_analysis_input(self, sol_id):
    analysis_dir = self.wctt_analysis_input_dir(sol_id)
    self.initialize_directory(analysis_dir)
    return self.make_solution_filename(analysis_dir, sol_id) + ".csv"

  def wctt_analysis_output(self, sol_id):
    return "timing-analysis-results/" + self.wctt_analysis_filename(sol_id)

  def remaining_time_budget(self):
    used_budget = datetime.now() - self.start_time_solving
    return timedelta(seconds = self.timeout_sec - used_budget.total_seconds())


class ParetoFront:
  def __init__(self, minimize_objs_str):
    self.minimize_objs = [bool(obj) for obj in minimize_objs_str]
    self.front = []
    self.sols = 0

  def num_found_solutions(self):
    return self.sols

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
    self.front = list(filter(lambda objs: not self.dominates(new_objs, objs[0]), self.front))
    self.front.append((new_objs, self.sols))
    self.sols = self.sols + 1

  def objective_mzn(self, objs, i):
    if self.minimize_objs[i]:
      return f"objs[{i+1}] < {objs[i]}"
    else:
      return f"objs[{i+1}] > {objs[i]}"

  def front_to_mzn(self):
    cons = "constraint ("
    for i in range(len(self.front)):
      objs = self.front[i][0]
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
      print(s[0])

def create_output_dzn(config, res, sol_id):
  output_dzn = config.output_dzn(sol_id)
  shutil.copyfile(config.input_dzn, output_dzn)
  with open(output_dzn, 'a') as odzn:
    solution = asdict(res.solution)
    for k,v in solution.items():
      if(isinstance(v, list)):
        odzn.write(k + "=" + str(v) + ";\n")

def create_output_topology(config, sol_id):
  output = subprocess.run([config.dzn2topology(), config.input_topology, config.output_dzn(sol_id)], text=True, capture_output=True)
  if output.returncode == 0:
    with open(config.output_topology(sol_id), 'w') as otopo:
      otopo.write(output.stdout)
  else:
    sys.exit("Error converting the DZN file " + output_dzn + " to a topology.\nstderr:\n" + output.stderr)

def create_wctt_analysis(config, sol_id):
  shutil.copyfile(config.output_topology(sol_id), config.wctt_analysis_input(sol_id))
  output = subprocess.run(["java", "-jar", config.wctt_analyser(), config.wctt_analysis_input_dir(sol_id)], text=True, capture_output=True)
  if output.returncode != 0:
    sys.exit("Error analyzing the topology file " + output_dzn + ".\nstdout:\n" + output.stdout + "\nstderr:\n" + output.stderr)

# If it is unschedulable, we force the charge of at least one link to be less than its current charge.
def create_conflict_charge(res):
  disjunction = []
  for i in range(len(res["charge"])):
    c = res["charge"][i]
    disjunction.append(f"charge[{i+1}] < {c}")
  return ' \\/ '.join(disjunction)

def create_conflict_max_charge(res):
  max_charge = 0
  max_i = 0
  for i in range(len(res["charge"])):
    c = int(res["charge"][i])
    if c > max_charge:
      max_charge = c
      max_i = i
  return f"charge[{max_i+1}] < {max_charge}"

def create_conflict_alloc(instance, service_name, res):
  services2names = instance["services2names"]
  i = services2names.index(service_name)
  loc = res["services2locs"][i]
  return f"services2locs[{i+1}] != {loc}"

def analyse_wctt_result(config, instance, res, sol_id):
  with open(config.wctt_analysis_output(sol_id), 'r') as fanalysis:
    for _ in range(5):
      next(fanalysis)
    wctt = csv.DictReader(fanalysis, delimiter=';')
    for row in wctt:
      # if the column slack is empty, it means the frame is scheduled using a best-effort strategy so no hard deadline.
      if row["Slack(ms)"] != '' and float(row["Slack(ms)"]) < 0:
        print(row["Name"] + ";" + row["Routing"] + ";" +row["Slack(ms)"])
        # return create_conflict_charge(res)
        # return create_conflict_max_charge(res)
        return create_conflict_alloc(instance, row["Name"], res)
    return "false"

def underappx_analysis(config, instance, res, sol_id):
  create_output_dzn(config, res, sol_id)
  create_output_topology(config, sol_id)
  create_wctt_analysis(config, sol_id)
  return analyse_wctt_result(config, instance, res, sol_id)

def osolve(config, instance):
  res = instance.solve(optimisation_level=3, timeout=config.remaining_time_budget())
  if res.solution is not None:
    print(res.solution)
  return res

def usolve_mo(config, instance, pareto_front):
  res = osolve(config, instance)
  conflict_constraints = ""
  while res.status == Status.SATISFIED:
    with instance.branch() as child:
      conflict = underappx_analysis(config, instance, res, pareto_front.num_found_solutions())
      if conflict == "false":
        pareto_front.push_sol(res['objs'])
        pareto_front.print()
        print(pareto_front.front_to_mzn())
        child.add_string(pareto_front.front_to_mzn())
      else:
        print("Found conflict: " + conflict)
        conflict_constraints += f"constraint {conflict};\n"
      time_budget = config.remaining_time_budget()
      if time_budget.total_seconds() <= 0:
        return
      print("Time left: " + str(time_budget.total_seconds()) + "s")
      child.add_string(conflict_constraints)
      res = osolve(config, child)

if __name__ == "__main__":
  config = Config()
  model = Model(config.input_mzn)
  model.add_file(config.input_dzn, parse_data=True)
  model.add_file(config.objectives_dzn, parse_data=True)
  solver = Solver.lookup(config.solver_name)
  instance = Instance(solver, model)
  pareto_front = ParetoFront(instance['minimize_objs'])
  try:
    usolve_mo(config, instance, pareto_front)
  except Exception as e:
    logging.error(traceback.format_exc())
  for _, sol_id in pareto_front.front:
    shutil.copyfile(config.output_dzn(sol_id), config.output_clean_dzn(sol_id))
    shutil.copyfile(config.output_topology(sol_id), config.output_clean_topology(sol_id))
