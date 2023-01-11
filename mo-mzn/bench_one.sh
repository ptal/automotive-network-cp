#!/bin/sh
set -x

data_name=$(basename -- "$1" .dzn)
res_dir=gecode_firstfail_random/$data_name
mkdir -p $res_dir
python3 mo.py $data_name --model_mzn="../model/automotive-sat.mzn" --objectives_dzn="../model/objectives.dzn" --dzn_dir="../data/dzn/cpu-60-percent" --topology_dir="../data/raw-csv" --solver_name="gecode" --timeout_sec=7200 --results_dir=$res_dir --bin="../bin"
