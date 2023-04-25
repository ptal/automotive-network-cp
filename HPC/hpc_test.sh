#!/bin/bash -l
#SBATCH --time=00:10:00
#SBATCH --partition=batch
#SBATCH --nodes=1
#SBATCH --mem=0
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=16

ulimit -u 10000
module load compiler/GCC/10.2.0
module load compiler/GCCcore/10.2.0
module load lang/Python/3.8.6-GCCcore-10.2.0
module load lang/Java/16.0.1
export PATH=$PATH:$HOME/.local/bin:$HOME/bin:$HOME/deps/gecode:$HOME/deps/libminizinc/build
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$HOME/deps/gecode
source ../mo-mzn/hpcpy/bin/activate

cd ../minizinc-mo
strategy="firstfail-random"
cp_timeout_sec=60
solver="gecode"
summary="../results/summary_hpc_test.csv"
res_dir="../results"

echo "Start Loop, yeay."

tasks_counter=1

algorithm="osolve-mo-then-uf"
for f in ../data/dzn/*50*005_u20.dzn;
do
  if [ -f $f ]
  then
    data_name=$(basename -- "$f" .dzn)
    log_file=$res_dir"/"$cp_strategy"_"$algorithm"_"$cp_timeout_sec"_"$data_name
    echo "Start srun...."$res_dir
    srun --exclusive --cpu-bind=cores -n1 -c16 python3 main.py --model_mzn "../model/automotive-sat.mzn" --objectives_dzn "../model/objectives.dzn" --dzn_dir "../data/dzn/" --topology_dir "../data/raw-csv" --solver_name "$solver" --cp_timeout_sec $cp_timeout_sec --tmp_dir "$res_dir" --bin "../bin" --summary "$summary" --uf_conflict_strategy "na" --uf_conflicts_combinator "na" --cp_strategy="$cp_strategy" --fzn_optimisation_level 1 --algorithm "$algorithm" "$data_name" | tee -a $res_dir/"output.txt" &
    wait
    let tasks_counter++
  fi
done
wait
