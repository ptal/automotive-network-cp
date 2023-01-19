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
import multiprocessing
from pymoo.indicators.hv import HV
import numpy as np
import copy

class Statistics:
  def __init__(self, summary_filename):
    self.cp_solutions = 0
    self.exhaustive = False
    self.cp_total_nodes = 0    # Total nodes explored.
    self.cp_total_nodes_to_sol = 0    # Total nodes explored.
    self.time_first_uf_sol = 0 # Time required to reach the first UF solution.
    self.time_last_uf_sol = 0 # Time required to reach the latest best UF solution.
    self.uf_solutions = 0
    self.best_pareto_front = []
    self.time_uf = 0
    self.time_cp = 0
    self.time_preprocess = 0
    self.total_time = 0
    self.uf_conflicts = 0
    self.uf_conflicts_backtrack = 0
    self.summary_filename = summary_filename

  def csv_header(self):
    if not os.path.exists(self.summary_filename):
      with open(self.summary_filename, "w") as summary:
        summary.write("instance;solver;algorithm;cp_strategy;uf_strategy;hypervolume;best_pareto_front;exhaustive;cp_solutions;uf_solutions;time_preprocess;time_cp;time_uf;total_time;time_first_uf_sol;time_last_uf_sol;cp_total_nodes;cp_average_nodes_to_sol;uf_conflicts;uf_conflicts_backtrack;cores;timeout_sec\n")

  def csv_entry(self, instance, config, pareto_front):
    hypervolume = pareto_front.hypervolume(instance)
    front = pareto_front.to_str()
    if self.cp_solutions != 0:
      cp_average_nodes_to_sol = self.cp_total_nodes_to_sol / self.cp_solutions
    else:
      cp_average_nodes_to_sol = 0
    with open(self.summary_filename, "a") as summary:
      summary.write(f"{config.data_name};{config.solver_name};{config.algorithm};{config.cp_strategy};{config.uf_strategy};{int(np.rint(hypervolume))};{front};{self.exhaustive};{self.cp_solutions};{self.uf_solutions};{round(self.time_preprocess,2)};{round(self.time_cp,2)};{round(self.time_uf,2)};{round(self.total_time,2)};{round(self.time_first_uf_sol,2)};{round(self.time_last_uf_sol,2)};{self.cp_total_nodes};{round(cp_average_nodes_to_sol,2)};{self.uf_conflicts};{self.uf_conflicts_backtrack};{config.cores};{config.timeout_sec}\n")


class Config:
  def __init__(self):
    parser = argparse.ArgumentParser(
                prog = 'cusolve_mo',
                description = 'Multi-objective constraint programming with WCTT. This program computes a Pareto front of the deployment problem on switch-based network.')
    parser.add_argument('instance_name')
    parser.add_argument('--model_mzn', required=True)
    parser.add_argument('--objectives_dzn', required=True)
    parser.add_argument('--dzn_dir', required=True)
    parser.add_argument('--topology_dir', required=True)
    parser.add_argument('--solver_name', required=True)
    parser.add_argument('--timeout_sec', required=True, type=int)
    parser.add_argument('--results_dir', required=True)
    parser.add_argument('--bin', required=True)
    parser.add_argument('--summary', required=True)
    parser.add_argument('--uf_strategy', required=True)
    parser.add_argument('--cp_strategy', required=True)
    parser.add_argument('--algorithm', required=True)
    args = parser.parse_args()
    self.data_name = args.instance_name
    self.input_mzn = args.model_mzn
    self.objectives_dzn = args.objectives_dzn  # Just because parameters directly in the mzn files are not accessible through the Python API...
    self.input_dzn = args.dzn_dir + "/" + self.data_name + ".dzn"
    topology_name = self.data_name
    while topology_name[-1] != '_':
      topology_name = topology_name[:-1]
    topology_name = topology_name[:-1]
    self.input_topology = args.topology_dir + "/" + topology_name + ".csv"
    self.solver_name = args.solver_name
    self.timeout_sec = args.timeout_sec
    self.results_dir = args.results_dir + "/results"
    self.all_results_dir = args.results_dir + "/all_results"
    self.bin_dir = args.bin
    self.summary = args.summary
    self.uf_strategy = args.uf_strategy
    self.cp_strategy = args.cp_strategy
    self.algorithm = args.algorithm
    self.start_time_solving = datetime.now()
    self.initialize_directory(self.all_results_dir)
    self.initialize_directory(self.results_dir)

  def initialize_cores(self, solver):
    if "-p" in solver.stdFlags:
      self.cores = multiprocessing.cpu_count() * 2
    else:
      self.cores = 1

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

  def time_elapsed(self):
    return datetime.now() - self.start_time_solving

  def remaining_time_budget(self):
    used_budget = self.time_elapsed()
    return timedelta(seconds = self.timeout_sec - used_budget.total_seconds())

class ParetoFront:
  def __init__(self, minimize_objs_str):
    self.minimize_objs = [bool(obj) for obj in minimize_objs_str]
    self.front = []
    self.sols = 0
    self.record_res = False
    self.keep_all = False

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

  def push_sol(self, sol, sol_id = None):
    # By construction, `objs` cannot be dominated by any solutions in the Pareto front.
    new_objs = [int(obj) for obj in sol['objs']]
    # We keep a solution in the Pareto front if at least one of its objective is strictly higher than the corresponding one in the new solution.
    # In other terms, we keep all solutions that are not dominated by `new_objs`.
    if not self.keep_all:
      self.front = list(filter(lambda objs: not self.dominates(new_objs, objs[0]), self.front))
    if sol_id == None:
      sol_id = self.sols
    if self.record_res:
      self.front.append((new_objs, sol_id, sol))
    else:
      self.front.append((new_objs, sol_id, None))
    self.sols = self.sols + 1

  def objective_mzn(self, objs, i):
    if self.minimize_objs[i]:
      return f"objs[{i+1}] < {objs[i]}"
    else:
      return f"objs[{i+1}] > {objs[i]}"

  def front_to_mzn(self):
    if len(self.front) == 0:
      return "constraint true;"
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

  def to_str(self):
    return '{' + ','.join([str(s[0]) for s in self.front]) + '}'

  def hypervolume(self, instance):
    if self.front == []:
      return 0
    ref_point = np.array(instance["ref_point"])
    front = np.array([f[0] for f in self.front])
    # pymoo only takes into consideration minimization, so we negate the objectives to maximize.
    for i in range(len(self.minimize_objs)):
      if not self.minimize_objs[i]:
        ref_point[i] = -ref_point[i]
        for point in front:
          point[i] = -point[i]
    return HV(ref_point=ref_point)(front)

def create_output_dzn(config, solution, sol_id):
  output_dzn = config.output_dzn(sol_id)
  shutil.copyfile(config.input_dzn, output_dzn)
  with open(output_dzn, 'a') as odzn:
    for k,v in solution.items():
      if(isinstance(v, list)):
        odzn.write(k + "=" + str(v) + ";\n")

def create_output_topology(config, sol_id):
  output = subprocess.run([config.dzn2topology(), config.input_topology, config.output_dzn(sol_id)], text=True, capture_output=True)
  if output.returncode == 0:
    with open(config.output_topology(sol_id), 'w') as otopo:
      otopo.write(output.stdout)
  else:
    sys.exit("Error converting the DZN file " + config.output_dzn(sol_id) + " to a topology.\nstderr:\n" + output.stderr)

def create_wctt_analysis(config, sol_id):
  shutil.copyfile(config.output_topology(sol_id), config.wctt_analysis_input(sol_id))
  output = subprocess.run(["java", "-jar", config.wctt_analyser(), config.wctt_analysis_input_dir(sol_id)], text=True, capture_output=True)
  if output.returncode != 0:
    sys.exit("Error analyzing the topology file " + config.output_dzn(sol_id) + ".\nstdout:\n" + output.stdout + "\nstderr:\n" + output.stderr)

def get_index_loc_from_name(instance, service_name, sol):
  services2names = instance["services2names"]
  i = services2names.index(service_name)
  loc = sol["services2locs"][i]
  return i, loc

def get_target_service(instance, service_from, loc_from, sol):
  service_to = -1
  loc_to = 0
  for x in range(len(instance["coms"][service_from])):
    loc_to = sol["services2locs"][x]
    if instance["coms"][service_from][x] != 0 and loc_from != loc_to:
      service_to = x
      break
  if service_to == -1:
    exit("Bug, a service has no communication in coms, but still had a negative delay for a communication...")
  return service_to, loc_to

def not_assignment(sol):
  disjunction = []
  for i in range(len(sol["services2locs"])):
    c = sol["services2locs"][i]
    disjunction.append(f"services2locs[{i+1}] != {c}")
  return '(' + (' \\/ '.join(disjunction)) + ')'

# If it is unschedulable, we force the charge of at least one link to be less than its current charge.
def decrease_all_link_charge(sol):
  disjunction = []
  for i in range(len(sol["charge"])):
    c = sol["charge"][i]
    disjunction.append(f"charge[{i+1}] < {c}")
  return ' \\/ '.join(disjunction)

def decrease_max_link_charge(sol):
  max_charge = 0
  max_i = 0
  for i in range(len(sol["charge"])):
    c = int(sol["charge"][i])
    if c > max_charge:
      max_charge = c
      max_i = i
  return f"charge[{max_i+1}] < {max_charge}"

def forbid_source_alloc(instance, service_name, sol):
  service_from, loc_from = get_index_loc_from_name(instance, service_name, sol)
  service_to, loc_to = get_target_service(instance, service_from, loc_from, sol)
  return f"services2locs[{service_from+1}] != {loc_from} /\\ services2locs[{service_from+1}] != {loc_to}"

def forbid_target_alloc(instance, service_name, sol):
  service_from, loc_from = get_index_loc_from_name(instance, service_name, sol)
  service_to, loc_to = get_target_service(instance, service_from, loc_from, sol)
  return f"services2locs[{service_to+1}] != {loc_to} /\\ services2locs[{service_to+1}] != {loc_from}"

def forbid_source_target_alloc(combination, instance, service_name, sol):
  return forbid_source_alloc(instance, service_name, sol) + combination + forbid_target_alloc(instance, service_name, sol)

def decrease_hop(instance, service_name, sol):
  service_from, loc_from = get_index_loc_from_name(instance, service_name, sol)
  service_to, loc_to = get_target_service(instance, service_from, loc_from, sol)
  return f"card(shortest_path[services2locs[{service_from+1}], services2locs[{service_to+1}]]) < card(shortest_path[{loc_from},{loc_to}])"

def all5(instance, service_name, sol):
  return decrease_all_link_charge(sol) + "/\\" + decrease_max_link_charge(sol) + " /\\ " + forbid_source_target_alloc(" /\\ ", instance, service_name, sol) + " /\\ " + decrease_hop(instance, service_name, sol)

def analyse_wctt_result(config, instance, sol, sol_id):
  with open(config.wctt_analysis_output(sol_id), 'r') as fanalysis:
    for _ in range(5):
      next(fanalysis)
    wctt = csv.DictReader(fanalysis, delimiter=';')
    conflict = "true"
    for row in wctt:
      # if the column slack is empty, it means the frame is scheduled using a best-effort strategy so no hard deadline.
      if row["Slack(ms)"] != '' and float(row["Slack(ms)"]) < 0:
        print("WCTT: " + row["Name"] + ";" + row["Routing"] + ";" +row["Slack(ms)"])
        if config.uf_strategy == "not_assignment":
          conflict += " /\\ " + not_assignment(sol)
        elif config.uf_strategy == "decrease_all_link_charge":
          conflict += " /\\ " + decrease_all_link_charge(sol)
        elif config.uf_strategy == "decrease_max_link_charge":
          conflict += " /\\ " + decrease_max_link_charge(sol)
        elif config.uf_strategy == "forbid_source_alloc":
          conflict += " /\\ " + forbid_source_alloc(instance, row["Name"], sol)
        elif config.uf_strategy == "forbid_target_alloc":
          conflict += " /\\ " + forbid_target_alloc(instance, row["Name"], sol)
        elif config.uf_strategy == "forbid_source_or_target_alloc":
          conflict += " /\\ " + forbid_source_target_alloc(" \\/ ", instance, row["Name"], sol)
        elif config.uf_strategy == "forbid_source_and_target_alloc":
          conflict += " /\\ " + forbid_source_target_alloc(" /\\ ", instance, row["Name"], sol)
        elif config.uf_strategy == "decrease_hop":
          conflict += " /\\ " + decrease_hop(instance, row["Name"], sol)
        elif config.uf_strategy == "all5":
          conflict += " /\\ " + all5(instance, row["Name"], sol)
        else:
          exit(f"Unknown uf_strategy {uf_strategy}")
    return conflict

def underappx_analysis(config, statistics, instance, sol, sol_id):
  time_start = config.time_elapsed()
  create_output_dzn(config, sol, sol_id)
  create_output_topology(config, sol_id)
  create_wctt_analysis(config, sol_id)
  wctt_res = analyse_wctt_result(config, instance, sol, sol_id)
  time_end = config.time_elapsed()
  statistics.time_uf += (time_end - time_start).total_seconds()
  return wctt_res

def osolve(config, statistics, instance, all_sols = False):
  sys.stdout.flush()
  # Note about optimisation_level: 0 and 1 take a similar amount of time.
  # 2 and 3 takes a substantial amount of time, i.e around half of the total time of the overall solving method.
  # 4 and 5 are way too long (because there are too many variables).
  if config.cores == 1:
    res = instance.solve(optimisation_level=1, all_solutions=all_sols, free_search=True, timeout=config.remaining_time_budget())
  else:
    res = instance.solve(optimisation_level=1, all_solutions=all_sols, free_search=True, processes=config.cores, timeout=config.remaining_time_budget())
  print(res.statistics)
  if res.solution is not None:
    if all_sols:
      statistics.cp_solutions += len(res.solution)
    else:
      statistics.cp_solutions += 1
  if "nodes" in res.statistics:
    statistics.cp_total_nodes += res.statistics["nodes"]
  if "solveTime" in res.statistics and "initTime" in res.statistics:
    statistics.time_cp += res.statistics["solveTime"].total_seconds() + res.statistics["initTime"].total_seconds()
  elif "time" in res.statistics:
    statistics.time_cp += res.statistics["time"] / 1000
  if "flatTime" in res.statistics:
    statistics.time_preprocess += res.statistics["flatTime"].total_seconds()
  return res

# `true` if the instance has been completely explored, `false` if we reached the timeout before.
def solve_mo(config, statistics, instance, pareto_front):
  res = osolve(config, statistics, instance)
  conflict_constraints = ""
  while res.status == Status.SATISFIED:
    with instance.branch() as child:
      pareto_front.push_sol(asdict(res.solution))
      print("Pareto front: " + pareto_front.to_str())
      child.add_string(pareto_front.front_to_mzn())
      time_budget = config.remaining_time_budget()
      if time_budget.total_seconds() <= 0:
        return False
      print("Time left: " + str(time_budget.total_seconds()) + "s")
      res = osolve(config, statistics, child)
  return res.status == Status.UNSATISFIABLE

# `true` if the instance has been completely explored, `false` if we reached the timeout before.
def usolve_mo(config, statistics, instance, pareto_front):
  res = osolve(config, statistics, instance)
  conflict_constraints = ""
  while res.status == Status.SATISFIED:
    with instance.branch() as child:
      conflict = underappx_analysis(config, statistics, instance, res.solution, pareto_front.num_found_solutions())
      if conflict == "true":
        pareto_front.push_sol(asdict(res.solution))
        pareto_front.print()
        child.add_string(pareto_front.front_to_mzn())
      else:
        print("Found conflict: " + conflict)
        conflict_constraints += f"constraint {conflict};\n"
      time_budget = config.remaining_time_budget()
      if time_budget.total_seconds() <= 0:
        return False
      print("Time left: " + str(time_budget.total_seconds()) + "s")
      child.add_string(conflict_constraints)
      res = osolve(config, statistics, child)
  return res.status == Status.UNSATISFIABLE

def conjunction_of(constraints):
  if len(constraints) == 0:
    return "constraint true;"
  else:
    return "constraint " + " /\\ ".join(constraints) + ";"

# `true` if the instance has been completely explored, `false` if we reached the timeout before.
def cusolve_mo(config, statistics, instance, pareto_front, conflicts):
  time_budget = config.remaining_time_budget()
  if time_budget.total_seconds() <= 0:
    return False
  print("Pareto front: " + pareto_front.to_str())
  print(f"Conflicts [{len(conflicts)}]: " + str(conflicts))
  print("Time left: " + str(time_budget.total_seconds()) + "s")
  with instance.branch() as child:
    child.add_string(pareto_front.front_to_mzn())
    child.add_string(conjunction_of(conflicts))
    res = osolve(config, statistics, child)
  if res.status == Status.SATISFIED:
    sol = asdict(res.solution)
    conflict = underappx_analysis(config, statistics, instance, sol, pareto_front.num_found_solutions())
    if conflict == "true":
      if pareto_front.num_found_solutions == 0:
        statistics.time_first_uf_sol = config.time_elapsed().total_seconds()
        statistics.time_last_uf_sol = statistics.time_first_uf_sol
      else:
        statistics.time_last_uf_sol = config.time_elapsed().total_seconds()
      statistics.uf_solutions += 1
      pareto_front.push_sol(sol)
      return cusolve_mo(config, statistics, instance, pareto_front, conflicts)
    else:
      statistics.uf_conflicts += 1
      if cusolve_mo(config, statistics, instance, pareto_front, conflicts + [conflict]):
        print("Backtraking happened when " + str(time_budget.total_seconds()) + "s were left.")
        statistics.uf_conflicts_backtrack += 1
        return cusolve_mo(config, statistics, instance, pareto_front, conflicts + [f"not ({conflict})"])
      else:
        return False
  return res.status == Status.UNSATISFIABLE

def solve_mo_then_uf(config, statistics, instance, pareto_front, keep_all):
  pareto_front.record_res = True
  pareto_front.keep_all = keep_all
  status = solve_mo(config, statistics, instance, pareto_front)
  uf_pareto_front = ParetoFront(instance['minimize_objs'])
  for f in pareto_front.front:
    conflict = underappx_analysis(config, statistics, instance, f[2], f[1])
    if conflict == "true":
      statistics.uf_solutions += 1
      uf_pareto_front.push_sol(f[2], f[1])
      uf_pareto_front.print()
  return uf_pareto_front

def solve_all_then_uf(config, statistics, instance):
  res = osolve(config, statistics, instance, True)
  if res.status == Status.ALL_SOLUTIONS:
    statistics.exhaustive = True
  uf_pareto_front = ParetoFront(instance['minimize_objs'])
  print(f"Found {len(res.solution)}")
  for sol_id in range(len(res.solution)):
    sol = asdict(res[sol_id])
    conflict = underappx_analysis(config, statistics, instance, sol, sol_id)
    if conflict == "true":
      statistics.uf_solutions += 1
      uf_pareto_front.push_sol(sol)
      uf_pareto_front.print()
  return uf_pareto_front

def already_computed(config):
  if os.path.exists(config.summary):
    with open(config.summary, 'r') as fsummary:
      summary = csv.DictReader(fsummary, delimiter=';')
      for row in summary:
        # Note that only cusolve-mo uses the uf_strategy, so we do not care about this property for other algorithms.
        if row["instance"] == config.data_name and row["solver"] == config.solver_name and row["algorithm"] == config.algorithm and row["cp_strategy"] == config.cp_strategy and (row["uf_strategy"] == config.uf_strategy or config.algorithm != "cusolve-mo") and row["timeout_sec"] == str(config.timeout_sec):
          return True
  return False

if __name__ == "__main__":
  config = Config()
  statistics = Statistics(config.summary)
  if already_computed(config):
    print(f"Skipping {config.results_dir} because it is already in {config.summary}")
    exit(0)
  else:
    print(f"Start computing {config.results_dir}")
  model = Model(config.input_mzn)
  model.add_file(config.input_dzn, parse_data=True)
  model.add_file(config.objectives_dzn, parse_data=True)
  solver = Solver.lookup(config.solver_name)
  config.initialize_cores(solver)
  instance = Instance(solver, model)
  pareto_front = ParetoFront(instance['minimize_objs'])
  try:
    if config.algorithm == "solve-mo-then-uf":
      pareto_front = solve_mo_then_uf(config, statistics, instance, pareto_front, False)
    elif config.algorithm == "solve-mo-keep-all-then-uf":
      pareto_front = solve_mo_then_uf(config, statistics, instance, pareto_front, True)
    elif config.algorithm == "solve-all-then-uf":
      pareto_front = solve_all_then_uf(config, statistics, instance)
    elif config.algorithm == "cusolve-mo":
      if cusolve_mo(config, statistics, instance, pareto_front, []):
      # if usolve_mo(config, statistics, instance, pareto_front):
        print("Problem completely explored.")
        statistics.exhaustive = True
      else:
        print("Timeout reached.")
    else:
      exit(f"Unknown algorithm {config.algorithm}")
  except Exception as e:
    logging.error(traceback.format_exc())
  statistics.total_time = config.time_elapsed().total_seconds()
  statistics.csv_header()
  statistics.csv_entry(instance, config, pareto_front)
  for f in pareto_front.front:
    sol_id = f[1]
    shutil.copyfile(config.output_dzn(sol_id), config.output_clean_dzn(sol_id))
    shutil.copyfile(config.output_topology(sol_id), config.output_clean_topology(sol_id))
