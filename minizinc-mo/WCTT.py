import shutil
import subprocess
import sys
import csv
from tempfile import TemporaryDirectory
import pexpect
import socket

class WCTT:
  """Given an assignment of services to processors, we run a worst-case traversal time analysis to check if it is a solution w.r.t. WTCC.
     Here is the workflow to perform the analysis:
      1. Convert the solution to a DZN file `solution.dzn`.
      2. Call the dzn2topology tool to convert the DZN file to a topology file `topology.csv`.
      3. Call the PEGASE timing analysis tool to perform the analysis on that file.
      4. Analyze the output of the PEGASE timing analysis tool and extract a conflict if it is unsuccessful.

     Args:
      instance (Instance): The instance of the MiniZinc constraint problem.
      config (Config): The configuration of the solving algorithm.
      conflict_combinator (String): The combinator used to combine the conflicts found by the strategy `config.uf_conflict_strategy`.
        It can be either " /\\ " (and) or " \\/ " (or).
        If you are not using `CUSolve` and use over-approximating conflicts, we must use " \// " (or), otherwise the algorithm might miss solutions.
      verbose (Bool): Print the steps of the analysis.
  """

  def _start_wctt_server(self):
    """Start the Pegase WCTT server.
       We start the Pegase program with `pexpect.spawn` and expect the program to print an integer which is the port number.
       After, Python will communicate using socket programming with the Pegase program."""
    self._print("Starting the Pegase WCTT server...")
    self.host = "localhost"
    self.input_topology = self.tmp_dir.name + "/input_topology.csv"
    self.output_wctt = self.tmp_dir.name + "/output_wctt.csv"
    self.wctt_process = pexpect.spawn("java", ["-jar", self.config.wctt_analyser, self.input_topology, self.output_wctt], encoding="utf-8")
    self.port = int(self.wctt_process.readline())
    self.wctt_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.wctt_socket.connect((self.host, self.port))

  def __init__(self, instance, config, conflict_combinator = " /\\ ", verbose = True):
    self.instance = instance
    self.config = config
    self.tmp_dir = TemporaryDirectory(dir=config.tmp_dir)
    self.conflict_combinator = conflict_combinator
    self.verbose = verbose
    self._start_wctt_server()
    self._print("WCTT temporary directory: " + self.tmp_dir.name)

  def analyse(self, sol, conflict_strategy="not_assignment"):
    """Perform the WCTT analysis on `sol` and produce a conflict on unschedulable solution.
       Args:
         sol (Solution): The MiniZinc solution to analyse.
         conflict_strategy (String): The strategy to use to create the conflict, it must be the name of a conflict method of this class.
       Returns: A string describing the conflict as a MiniZinc constraint if the solution is not schedulable, `True` otherwise.
    """
    solution_dzn = self._solution2dzn(sol)
    self._dzn2topology(solution_dzn)
    self._topology2analysis()
    return self._create_conflict(sol, conflict_strategy)

  def _print(self, msg):
    if self.verbose:
      print(msg)

  def _solution2dzn(self, solution):
    """Convert `solution` to the DZN format in a file `solution.dzn` in the temporary directory.
       Then, append to it the input parameter DZN file."""
    solution_dzn = self.tmp_dir.name + "/solution.dzn"
    self._print("solution2dzn: " + solution_dzn)
    shutil.copyfile(self.config.input_dzn, solution_dzn)
    with open(solution_dzn, 'a') as odzn:
      for k in vars(solution):
        odzn.write(k + " = " + str(getattr(solution, k)) + ";\n")
    return solution_dzn

  def _dzn2topology(self, solution_dzn):
    """Convert the DZN file to a topology file named `topology.csv` in the temporary directory."""
    self._print("dzn2topology: " + self.config.input_topology)
    output = subprocess.run([self.config.dzn2topology(), self.config.input_topology, solution_dzn], text=True, capture_output=True)
    if output.returncode != 0:
      with open(solution_dzn, 'r') as fin:
        print(fin.read())
      sys.exit("Error converting the DZN file solution.dzn in the temporary directory to a topology.\nstdout:\n" + output.stdout + "\nstderr:\n" + output.stderr)
    topology = self.tmp_dir.name + "/topology.csv"
    with open(topology, 'w') as otopo:
      otopo.write(output.stdout)

  def _topology2analysis_async(self, analysis_precision = 1):
    self._print("topology2analysis_async")
    self.wctt_socket.sendall(bytes(str(analysis_precision)+"\n", "utf-8"))
    result = self.wctt_socket.recv(1024).decode()
    if result != "done\n":
      sys.exit("Error analyzing the topology file `topology.csv` in the temporary directory.\nstdout:\n" + self.wctt_process.stdout + "\nstderr:\n" + self.wctt_process.stderr)

  def _topology2analysis(self):
    """Run the Pegase WCTT analysis on the temporary directory containing the topology to analyze."""
    self._print("topology2analysis")
    output = subprocess.run(["java", "-jar", self.config.wctt_analyser(), self.tmp_dir.name], text=True, capture_output=True)
    if output.returncode != 0:
      sys.exit("Error analyzing the topology file `topology.csv` in the temporary directory.\nstdout:\n" + output.stdout + "\nstderr:\n" + output.stderr)

  def _create_conflict(self, sol, conflict_strategy):
    """Analyse the result of the WCTT analysis (in `timing-analysis-results/topology_WCTT.csv`) and extract a conflict if it is unsuccessful, otherwise returns True."""
    self._print("create_conflict: " + conflict_strategy)
    with open(self.output_analysis, 'r') as fanalysis:
      for _ in range(5):
        next(fanalysis)
      wctt = csv.DictReader(fanalysis, delimiter=';')
      conflicts = []
      conflict_gen = getattr(self, conflict_strategy)
      for row in wctt:
        # if the column slack is empty, it means the frame is scheduled using a best-effort strategy so no hard deadline.
        if row["Slack(ms)"] != '' and float(row["Slack(ms)"]) < 0:
          self._print("WCTT conflict: " + row["Name"] + ";" + row["Routing"] + ";" +row["Slack(ms)"])
          conflicts.append(conflict_gen(self, row, sol))
          if self.is_global_conflict():
            break
      if conflicts == []:
        return "true"
      else:
        return "(" + self.conflict_combinator.join(conflicts) + ")"

  def _is_global_conflict(self):
    """True if the conflict is global, i.e. it is a conflict on all the services and not only the ones directly responsible for the WCTT analysis failure."""
    return self.config.uf_conflict_strategy == "decrease_all_link_charge" \
        or self.config.uf_conflict_strategy == "decrease_max_link_charge" \
        or self.config.uf_conflict_strategy == "not_assignment"

  def _get_index_loc_from_loc_name(self, loc_name, sol):
    for i, x in enumerate(self.instance["locations2names"]):
      if x == loc_name:
        return i
    exit("Bug: The WCTT analysis produced a location name unknown to the constraint model...")

  def _get_index_loc_from_service_name(self, service_name, sol):
    """Given a service `service_name`, return its "service index" and the index of the processor on which the service is allocated on."""
    services2names = self.instance["services2names"]
    i = services2names.index(service_name)
    loc = sol["services2locs"][i]
    return i, loc

  def _get_target_service(self, service_from, loc_to, sol):
    """Given a service `service_from` that is communicating with a service on processor `loc_to`, find the index of the services it is communicating with.
       It is possible that several services placed on the same processor are communicating with `service_from`, in which case we return them all. """
    services_to = []
    for x in range(len(self.instance["coms"][service_from])):
      # If we communicate with `x` and `x` is placed on `loc_to`.
      if self.instance["coms"][service_from][x] != 0 and sol["services2locs"][x] == loc_to:
        services_to.append(x)
    if services_to == []:
      exit("Bug: a service has no communication in coms, but still had a negative delay for a communication...")
    return services_to

  def not_assignment(self, row, sol):
    """Given an assignment of services to locations, returns the logical negation of this assignment."""
    disjunction = []
    for i in range(len(sol["services2locs"])):
      c = sol["services2locs"][i]
      disjunction.append(f"services2locs[{i+1}] != {c}")
    return '(' + (' \\/ '.join(disjunction)) + ')'

  def decrease_one_link_charge(self, row, sol):
    """Given an assignment of services to locations, we force the load of at least one link to be strictly less than its current load."""
    disjunction = []
    for i in range(len(sol["charge"])):
      c = sol["charge"][i]
      disjunction.append(f"charge[{i+1}] < {c}")
    return ' \\/ '.join(disjunction)

  def decrease_max_link_charge(self, row, sol):
    """Given an assignment of services to locations, we force the load of the link with the highest load to be strictly less than its current load."""
    max_charge = 0
    max_i = 0
    for i in range(len(sol["charge"])):
      c = int(sol["charge"][i])
      if c > max_charge:
        max_charge = c
        max_i = i
    return f"charge[{max_i+1}] < {max_charge}"

  def forbid_source_alloc(self, row, sol):
    """Given a communication with negative slack described in `row`, forbid the service `row["Name"]` to be allocated on its current processor or the processor it is communicating with."""
    service_from, loc_from = self._get_index_loc_from_service_name(row["Name"], sol)
    loc_to = self._get_index_loc_from_loc_name(row["Receiver"], sol)
    return f"services2locs[{service_from+1}] != {loc_from} /\\ services2locs[{service_from+1}] != {loc_to}"

  def forbid_target_alloc(self, row, sol):
    """Given a communication with negative slack described in `row`, forbid one of the services communicating with `row["Name"]` to be allocated on the processor of `row["Name"]` or the processor it is currently allocated on."""
    service_from, loc_from = self._get_index_loc_from_service_name(row["Name"], sol)
    loc_to = self._get_index_loc_from_loc_name(row["Receiver"], sol)
    services_to = self._get_target_service(service_from, loc_to, sol)
    disjunction = []
    for s in services_to:
      disjunction.append(f"services2locs[{s+1}] != {loc_from} /\\ services2locs[{s+1}] != {loc_to}")
    return '(' + (' \\/ '.join(disjunction)) + ')'

  def _forbid_source_target_alloc(self, combinator, row, sol):
    return self.forbid_source_alloc(row, sol) + combinator + self.forbid_target_alloc(row, sol)

  def forbid_source_target_alloc_or(self, row, sol):
    """Combine the conflicts of `forbid_source_alloc` and `forbid_target_alloc` with a logical disjunction."""
    return self._forbid_source_target_alloc(' \\/ ', row, sol)

  def forbid_source_target_alloc_and(self, row, sol):
    """Combine the conflicts of `forbid_source_alloc` and `forbid_target_alloc` with a logical conjunction."""
    return self._forbid_source_target_alloc(' /\\ ', row, sol)

  def _decrease_hop(self, combinator, row, sol):
    service_from, loc_from = self._get_index_loc_from_service_name(row["Name"], sol)
    loc_to = self._get_index_loc_from_loc_name(row["Receiver"], sol)
    services_to = self._get_target_service(service_from, loc_to, sol)
    combination = []
    for s in services_to:
      combination.append(f"card(shortest_path[services2locs[{service_from+1}], services2locs[{s+1}]]) < card(shortest_path[{loc_from},{loc_to}])")
    return '(' + combinator.join(combination) + ')'

  def decrease_hop_or(self, row, sol):
    """Create a conflict forcing the number of hops of one of the services communicating with `row["Name"]` to be strictly less than the number of hops from `row["Name"]` to `row["Receiver"]`."""
    return self._decrease_hop(' \\/ ', row, sol)

  def decrease_hop_and(self, row, sol):
    """Create a conflict forcing the number of hops of all the services communicating with `row["Name"]` to be strictly less than the number of hops from `row["Name"]` to `row["Receiver"]`."""
    return self._decrease_hop(' /\\ ', row, sol)
