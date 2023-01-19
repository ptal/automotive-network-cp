#!/bin/bash
# set -x


# algorithms=("solve-mo-then-uf" "solve-mo-keep-all-then-uf" "solve-all-then-uf" "cusolve-mo")
algorithms=("cusolve-mo" "solve-mo-then-uf")
strategy=firstfail-inrandom

# uf_strategies2=("forbid_source_alloc" "decrease_hop" "all5")
uf_strategies2=("not_assignment" "decrease_hop" "forbid_source_alloc" "forbid_target_alloc" "forbid_source_or_target_alloc" "forbid_source_and_target_alloc")
timeout_sec=1200
solvers=("gecode")

for f in ../data/dzn/subset_small/*;
do
  if [ -f $f ]
  then
    data_name=$(basename -- "$f" .dzn)
    # if [ $data_name == "topology75-14_005_c20" ]
    # then
      for algorithm in ${algorithms[@]}; do
        for uf_strategy in ${uf_strategies2[@]}; do
          for solver in ${solvers[@]}; do
            res_dir="subset_small/"$solver"_"$strategy"_"$uf_strategy"_"$algorithm"/"$data_name
            mkdir -p $res_dir
            python3 mo.py "$data_name" --model_mzn="../model/automotive-sat.mzn" --objectives_dzn="../model/objectives.dzn" --dzn_dir="../data/dzn" --topology_dir="../data/raw-csv" --solver_name="$solver" --timeout_sec="$timeout_sec" --results_dir="$res_dir" --bin="../bin" --summary="summary_small.csv" --uf_strategy="$uf_strategy" --cp_strategy="$strategy" --algorithm="$algorithm" | tee -a $res_dir/"output.txt"
          done
        done
      done
    # fi
  fi
done

solver=gecode
strategy=free
timeout_sec=600

uf_strategies=("decrease_all_link_charge" "decrease_max_link_charge" "forbid_source_alloc" "forbid_target_alloc" "forbid_source_or_target_alloc" "forbid_source_and_target_alloc" "decrease_hop")


for f in ../data/dzn/subset_u80/*;
do
  if [ -f $f ]
  then
    data_name=$(basename -- "$f" .dzn)
    for uf_strategy in ${uf_strategies[@]}; do
      for algorithm in ${algorithms[@]}; do
        res_dir="subset_u80/"$solver"_"$strategy"_"$uf_strategy"_"$algorithm"/"$data_name
        mkdir -p $res_dir
        python3 mo.py "$data_name" --model_mzn="../model/automotive-sat.mzn" --objectives_dzn="../model/objectives.dzn" --dzn_dir="../data/dzn" --topology_dir="../data/raw-csv" --solver_name="$solver" --timeout_sec="$timeout_sec" --results_dir="$res_dir" --bin="../bin" --summary="summary_u80.csv" --uf_strategy="$uf_strategy" --cp_strategy="$strategy" --algorithm="$algorithm" | tee -a $res_dir/"output.txt"
      done
    done
  fi
done




uf_strategies2=("forbid_source_alloc" "decrease_hop" "all5")
timeout_sec=600
for f in ../data/dzn/subset_75/*;
do
  if [ -f $f ]
  then
    data_name=$(basename -- "$f" .dzn)
    for uf_strategy in ${uf_strategies2[@]}; do
      for algorithm in ${algorithms[@]}; do
        res_dir="subset_75/"$solver"_"$strategy"_"$uf_strategy"_"$algorithm"/"$data_name
        mkdir -p $res_dir
        python3 mo.py "$data_name" --model_mzn="../model/automotive-sat.mzn" --objectives_dzn="../model/objectives.dzn" --dzn_dir="../data/dzn" --topology_dir="../data/raw-csv" --solver_name="$solver" --timeout_sec="$timeout_sec" --results_dir="$res_dir" --bin="../bin" --summary="summary_75.csv" --uf_strategy="$uf_strategy" --cp_strategy="$strategy" --algorithm="$algorithm" | tee -a $res_dir/"output.txt"
      done
    done
  fi
done
