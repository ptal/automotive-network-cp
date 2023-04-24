import argparse
import multiprocessing

class Config:
  """Configuration class for the multi-objective constraint programming with WCTT.
     It parses the commandline arguments and initializes the temporary and result directories."""
  def __init__(self):
    parser = argparse.ArgumentParser(
                prog = 'mo_wctt',
                description = 'Multi-objective constraint programming with WCTT. This program computes a Pareto front of the deployment problem on switch-based network.')
    parser.add_argument('instance_name')
    parser.add_argument('--model_mzn', required=True)
    parser.add_argument('--objectives_dzn', required=True)
    parser.add_argument('--dzn_dir', required=True)
    parser.add_argument('--topology_dir', required=True)
    parser.add_argument('--solver_name', required=True)
    parser.add_argument('--cp_timeout_sec', required=True, type=int)
    parser.add_argument('--tmp_dir', required=True)
    parser.add_argument('--bin', required=True)
    parser.add_argument('--summary', required=True)
    parser.add_argument('--uf_conflict_strategy', required=True)    # Must be the name of a conflict method of WCTT (or "na" if non-applicable)
    parser.add_argument('--uf_conflicts_combinator', required=True) # Must be "and" or "or" (or "na" if non-applicable).
    parser.add_argument('--cp_strategy', required=True)             # Must be "free" or the name of a CP strategy (only for information purposes, the strategy must be described in the model).
    parser.add_argument('--algorithm', required=True)               # Must be either "solve-mo-then-uf" or "cusolve-mo".
    parser.add_argument('--fzn_optimisation_level', required=True, type=int)
    args = parser.parse_args()
    Config.clean_dir_name(args.bin)
    Config.clean_dir_name(args.topology_dir)
    Config.clean_dir_name(args.dzn_dir)
    Config.clean_dir_name(args.tmp_dir)
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
    self.cp_timeout_sec = args.cp_timeout_sec
    self.tmp_dir = args.tmp_dir
    self.bin_dir = args.bin
    self.summary_filename = args.summary
    self.uf_conflict_strategy = args.uf_conflict_strategy
    self.uf_conflicts_combinator = args.uf_conflicts_combinator
    self.cp_strategy = args.cp_strategy
    self.algorithm = args.algorithm
    self.fzn_optimisation_level = args.fzn_optimisation_level

  def clean_dir_name(dir):
    """Remove the last '/' if it exists."""
    if dir[-1] == '/':
      dir = dir[:-1]

  def init_statistics(self, statistics):
    statistics["instance"] = self.data_name
    statistics["algorithm"] = self.algorithm
    statistics["cp_solver"] = self.solver_name
    statistics["cp_strategy"] = self.cp_strategy
    statistics["uf_conflict_strategy"] = self.uf_conflict_strategy
    statistics["uf_conflicts_combinator"] = self.uf_conflicts_combinator
    statistics["fzn_optimisation_level"] = self.fzn_optimisation_level
    statistics["cores"] = self.cores
    statistics["cp_timeout_sec"] = self.cp_timeout_sec

  def initialize_cores(self, solver):
    """If the solver supports parallelization, use twice the number of available cores. Otherwise, use only one core."""
    if "-p" in solver.stdFlags:
      self.cores = multiprocessing.cpu_count() * 2
    else:
      self.cores = 1

  def wctt_analyser(self):
    return self.bin_dir + "/pegase-timing-analysis.jar"

  def dzn2topology(self):
    return self.bin_dir + "/dzn2topology"
