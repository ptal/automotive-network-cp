import csv
import ast
import matplotlib.pyplot as plt
import tikzplotlib
from tabulate import tabulate

class Experiment:
  def __init__(self, uid):
    self.cumul_time = 0.0
    self.score = 0.0
    self.uf_conflicts = 0
    self.uf_backtracks = 0
    self.uf_solutions = 0
    self.uid = uid
    self.rows = []
    self.num_best_hv = 0

  def make_uid(row):
    return row["algorithm"] + "_" + row["uf_conflict_strategy"] + "_" + row["uf_conflicts_combinator"] + "_" + str(row["cp_timeout_sec"])

  def time_of_last_solution(row):
    cp_solutions = ast.literal_eval(row["cp_solutions_list"])
    if row["algorithm"] == "osolve-mo-then-uf":
      return cp_solutions[-1]
    elif row["algorithm"] == "cusolve-mo":
      uf_solutions = ast.literal_eval(row["uf_solutions_list"])
      for cp, uf in zip(reversed(cp_solutions), reversed(uf_solutions)):
        if uf:
          return cp
      return 0.0
    else:
      assert False, ("Unknown algorithm " + row["algorithm"])

  def add_instance(self, row):
    self.rows.append(row)
    self.cumul_time += Experiment.time_of_last_solution(row)
    self.uf_conflicts += int(row["uf_conflicts"])
    if row["uf_conflicts_backtrack"] != "":
      self.uf_backtracks += int(row["uf_conflicts_backtrack"])
    self.uf_solutions += int(row["uf_solutions"])

  def short_name(self):
    if self.rows[0]['algorithm'] == "osolve-mo-then-uf":
      return "MO_UF"
    else:
      if self.rows[0]['uf_conflict_strategy'] == 'not_assignment':
        return "NA"
      if self.rows[0]['uf_conflict_strategy'] == 'decrease_one_link_charge':
        return "D1L"
      if self.rows[0]['uf_conflict_strategy'] == 'decrease_max_link_charge':
        return "DML"
      if self.rows[0]['uf_conflict_strategy'] == 'forbid_target_alloc':
        if self.rows[0]['uf_conflicts_combinator'] == 'or':
          return "FTO"
        else:
          return "FTA"
      if self.rows[0]['uf_conflict_strategy'] == 'forbid_source_alloc':
        if self.rows[0]['uf_conflicts_combinator'] == 'or':
          return "FSO"
        else:
          return "FSA"
      if self.rows[0]['uf_conflict_strategy'] == 'forbid_source_target_alloc_and':
        if self.rows[0]['uf_conflicts_combinator'] == 'or':
          return "FSTO"
        else:
          return "FSTA"
      if self.rows[0]['uf_conflict_strategy'] == 'decrease_hop_and':
        if self.rows[0]['uf_conflicts_combinator'] == 'or':
          return "DHO"
        else:
          return "DHA"

class Instance:
  def __init__(self, name):
    self.name = name
    self.best_hv = 0.0

  def compute_best_hv(self, row):
    if row['instance'] == self.name:
      self.best_hv = max(float(row["hypervolume"]), self.best_hv)

class Algorithm:
  def __init__(self, name):
    self.name = name
    self.cumul_fzn_time = 0.0
    self.cumul_cp_time = 0.0
    self.cumul_uf_time = 0.0
    self.cp_solutions = 0
    self.uf_conflicts = 0

  def add(self, row):
    self.cumul_cp_time += float(row["time_cp_sec"])
    self.cumul_fzn_time += float(row["time_fzn_sec"])
    self.cumul_uf_time += float(row["uf_time_sec"])
    self.cp_solutions += int(row["cp_solutions"])
    self.uf_conflicts += int(row["uf_conflicts"])

  def __str__(self):
    total = self.cumul_cp_time + self.cumul_uf_time
    return self.name + "\n" + \
            "Total time: " + str(total) + ": \n" +\
            "  - CP: " + str((self.cumul_cp_time-self.cumul_fzn_time)/total * 100.) + "%\n" +\
            "  - FZN: " + str(self.cumul_fzn_time / total * 100.) + "%\n" +\
            "  - UF: " + str(self.cumul_uf_time / total * 100.) + "%\n" +\
            "Total solutions: " + str(self.cp_solutions) + "\n" +\
            "  - UF: " + str(float(self.cp_solutions-self.uf_conflicts) / self.cp_solutions * 100.) + "%\n"

class Campaign:
  def __init__(self, filename, keep):
    self.experiments = {}
    self.instances = {}
    self.algorithms = {"osolve-mo-then-uf": Algorithm("osolve-mo-then-uf"), "cusolve-mo": Algorithm("cusolve-mo")}
    with open(filename, 'r') as fresults:
      reader = csv.DictReader(fresults, delimiter=';')
      for row in reader:
        self.add_instance(row)
        if keep(row):
          self.algorithms[row['algorithm']].add(row)
          self.add_experiment(row)
    self.compute_statistics()

  def add_instance(self, row):
    name = row['instance']
    if name not in self.instances:
      self.instances[name] = Instance(name)
    self.instances[name].compute_best_hv(row)

  def add_experiment(self, row):
    uid = Experiment.make_uid(row)
    if uid not in self.experiments:
      self.experiments[uid] = Experiment(uid)
    self.experiments[uid].add_instance(row)

  def compute_statistics(self):
    for uid in self.experiments:
      for row in self.experiments[uid].rows:
        best_hv = self.instances[row['instance']].best_hv
        if best_hv == float(row["hypervolume"]):
          self.experiments[uid].num_best_hv += 1
        self.experiments[uid].score += float(row["hypervolume"]) / best_hv

  def sort_experiments_by_cumul_time(self):
    self.experiments = dict(sorted(self.experiments.items(), key=lambda item: item[1].cumul_time, reverse=True))

  def sort_experiments_by_score(self):
    self.experiments = dict(sorted(self.experiments.items(), key=lambda item: item[1].score, reverse=True))

  def sort_experiments_by_num_best_hv(self):
    self.experiments = dict(sorted(self.experiments.items(), key=lambda item: item[1].num_best_hv, reverse=True))

  def short_xp_names(self):
    return [e.short_name() for e in self.experiments.values()]

  def osolve_mo_then_uf_hv(self, timeout):
    uid = 'osolve-mo-then-uf_na_na_'+str(timeout)
    data = []
    for row in self.experiments[uid].rows:
      before = float(row['hypervolume_before_uf'])
      after = float(row['hypervolume'])
      data.append([row['instance'], before, after, after/before*100.])
    return data

def analyse(filename):
  timeout_sec = 1800
  campaign = Campaign(filename, lambda row: (\
    row["uf_conflict_strategy"] != "not_assignment" or row["uf_conflicts_combinator"] == "and" or\
    row["uf_conflict_strategy"] != "decrease_one_link_charge" or\
    row["uf_conflict_strategy"] != "decrease_max_link_charge") and int(row["cp_timeout_sec"]) == timeout_sec)
  fig, ax = plt.subplots()
  ax.spines['top'].set_visible(False)
  ax.spines['right'].set_visible(False)

  for s in campaign.algorithms.values():
    print(s)

  # campaign.sort_experiments_by_cumul_time()
  # campaign.sort_experiments_by_score()
  # red_bar = []
  # green_bar = []
  # for e in campaign.experiments.values():
  #   all = float(e.uf_conflicts + e.uf_solutions)
  #   red = e.uf_conflicts / all * e.score
  #   green = e.score - red
  #   red_bar.append(red)
  #   green_bar.append(green)

  # plt.ylabel("Score")
  # plt.bar(campaign.short_xp_names(), red_bar, color='red', label='UF conflicts')
  # plt.bar(campaign.short_xp_names(), green_bar, bottom=red_bar, color='green', label='UF solutions')
  # plt.legend()
  # plt.show()

  # campaign.sort_experiments_by_score()
  # plt.bar(campaign.short_xp_names(), [e.score for e in campaign.experiments.values()])
  # plt.legend()
  # plt.show()

  plt.ylabel("#Best hypervolumes")
  campaign.sort_experiments_by_num_best_hv()
  print([(e.uid, e.uf_solutions, e.uf_conflicts) for e in campaign.experiments.values()])
  plt.bar(campaign.short_xp_names(), [e.num_best_hv for e in campaign.experiments.values()])
  # plt.legend()
  # plt.show()

  # plt.bar(campaign.short_xp_names(), [e.cumul_time for e in campaign.experiments.values()])
  plt.xticks(fontsize=8)
  tikzplotlib.save("../paper/experiments.tex", axis_width="15cm", axis_height="7cm", textsize=8.0)

  print(tabulate(campaign.osolve_mo_then_uf_hv(timeout_sec), tablefmt="latex", floatfmt=".2f"))

analyse("summary_hpc.csv")
