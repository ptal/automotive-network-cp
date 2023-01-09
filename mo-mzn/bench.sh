#!/bin/sh
set -x

for f in ../data/dzn/*;
do
  if [ -f $f ]
  then
    data_name=$(basename -- "$f" .dzn)
    res_dir=gecode_firstfail_random/$data_name
    mkdir -p $res_dir
    python3 mo.py $data_name --model_mzn="../model/automotive-sat.mzn" --objectives_dzn="../model/objectives.dzn" --dzn_dir="../data/dzn" --topology_dir="../data/raw-csv" --solver_name="gecode" --timeout_sec=60 --results_dir=$res_dir --bin="../bin"
  fi
done
