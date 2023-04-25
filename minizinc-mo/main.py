from Config import *
from Sequence import *
from CUSolve import *
from MO import *
from OSolve import *
from USolve import *
from WCTT import *
from FilterWCTT import *
from Timer import *
from minizinc import Instance, Model, Solver
import csv
import os
import traceback
import logging
from filelock import FileLock
from tempfile import NamedTemporaryFile

def init_top_level_statistics(statistics):
  statistics["exhaustive"] = False
  statistics["hypervolume"] = 0
  statistics["datetime"] = datetime.now()

def main():
  config = Config()
  check_already_computed(config)
  model = Model(config.input_mzn)
  model.add_file(config.input_dzn, parse_data=True)
  model.add_file(config.objectives_dzn, parse_data=True)
  mzn_solver = Solver.lookup(config.solver_name)
  config.initialize_cores(mzn_solver)
  instance = Instance(mzn_solver, model)
  statistics = {}
  config.init_statistics(statistics)
  init_top_level_statistics(statistics)
  solver, pareto_front = build_solver(instance, config, statistics)
  try:
    statistics["exhaustive"] = False
    for x in solver.solve():
      pass
    print("Problem completely explored.")
    statistics["exhaustive"] = True
  except TimeoutError:
    pass
  except Exception as e:
    logging.error(traceback.format_exc())
  statistics["hypervolume"] = pareto_front.hypervolume()
  print(statistics)
  write_statistics(config, statistics)

def check_already_computed(config):
  if os.path.exists(config.summary_filename):
    with open(config.summary_filename, 'r') as fsummary:
      summary = csv.DictReader(fsummary, delimiter=';')
      for row in summary:
        # Note that only cusolve-mo uses the uf_conflict_strategy, so we do not care about this property for other algorithms.
        if row["instance"] == config.data_name and row["cp_solver"] == config.solver_name and row["algorithm"] == config.algorithm and row["cp_strategy"] == config.cp_strategy and ((row["uf_conflict_strategy"] == config.uf_conflict_strategy and row["uf_conflicts_combinator"] == config.uf_conflicts_combinator) or config.algorithm != "cusolve-mo") and row["fzn_optimisation_level"] == config.fzn_optimisation_level and row["cores"] == config.cores and row["timeout_sec"] == str(config.timeout_sec):
         print(f"Skipping {config.results_dir} because it is already in {config.summary}")
         exit(0)
  return False

def build_solver(instance, config, statistics):
  osolve = build_osolver(instance, config, statistics)
  osolve_mo = MO(instance, osolve)
  if config.algorithm == "osolve-mo":
    solver = osolve_mo
  else:
    wctt = WCTT(instance, config)
    if config.algorithm == "osolve-mo-then-uf":
      filterWCTT = FilterWCTT(statistics, osolve_mo.pareto_front, wctt)
      solver = Sequence([osolve_mo, filterWCTT], True)
    elif config.algorithm == "cusolve-mo":
      if config.uf_conflict_strategy == "not_assignment" and config.uf_conflicts_combinator == "or":
        solver = USolve(instance, statistics, osolve_mo, \
          lambda res: wctt.analyse(res.solution, config.uf_conflict_strategy, config.uf_conflicts_combinator))
      else:
        solver = CUSolve(instance, statistics, osolve_mo, \
          lambda res: wctt.analyse(res.solution, config.uf_conflict_strategy, config.uf_conflicts_combinator), \
          lambda res: wctt.create_conflict(res.solution, "not_assignment", "or"))
    else:
      exit(f"Unknown algorithm {config.algorithm}")
  return solver, osolve_mo.pareto_front

def build_osolver(instance, config, statistics):
  free_search = config.cp_strategy == "free_search"
  return OSolve(instance, statistics, Timer(config.cp_timeout_sec), config.threads, free_search, config.fzn_optimisation_level)

def csv_header(config):
  statistics = {}
  config.init_statistics(statistics)
  init_top_level_statistics(statistics)
  OSolve.init_statistics(statistics)
  USolve.init_statistics(statistics)
  CUSolve.init_statistics(statistics)
  FilterWCTT.init_statistics(statistics)
  return list(statistics.keys())

def create_summary_file(config):
  """We create the CSV summary file if it does not exist yet.
     The header of the summary file is the list of all the statistics the combinators can collect, even if the current solving algorithm do not use all of them.
     This is to be able to compare the statistics of different algorithms.
  """
  if not os.path.exists(config.summary_filename):
    with open(config.summary_filename, "w") as summary:
      writer = csv.DictWriter(summary, fieldnames=csv_header(config), delimiter=';')
      writer.writeheader()

def write_statistics(config, statistics):
  lock = FileLock(config.summary_filename + ".lock")
  with lock:
    create_summary_file(config)
    with open(config.summary_filename, "a") as summary:
      stats_keys = csv_header(config)
      csv_entry = ""
      for k in stats_keys:
        if k in statistics:
          csv_entry += str(statistics[k])
        csv_entry += ";"
      summary.write(csv_entry[:-1] + "\n")

if __name__ == "__main__":
  main()
