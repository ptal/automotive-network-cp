#!/bin/bash
set -x

solver=gecode
strategy=free
data_name=$(basename -- "$1" .dzn)

# algorithms=("solve-mo-then-uf" "solve-mo-keep-all-then-uf" "solve-all-then-uf" "cusolve-mo")
algorithms=("cusolve-mo")

for algorithm in ${algorithms[@]}; do
  res_dir=$solver"_"$strategy"_"$algorithm"/"$data_name
  mkdir -p $res_dir
  python3 mo.py $data_name --model_mzn="../model/automotive-sat.mzn" --objectives_dzn="../model/objectives.dzn" --dzn_dir="../data/dzn/cpu-60-percent" --topology_dir="../data/raw-csv" --solver_name="$solver" --timeout_sec=240 --results_dir="$res_dir" --bin="../bin" --summary="summary.csv" --uf_conflict_strategy="decrease_hop" --cp_strategy="$strategy" --algorithm="$algorithm" | tee $res_dir/"output.txt"
done