#!/bin/bash -l
#SBATCH --time=00:05:00
#SBATCH --partition=batch
#SBATCH --nodes=1
#SBATCH --mem=0
#SBATCH --ntasks-per-node=8
#SBATCH --cpus-per-task=16
#SBATCH -w aion-0180

ulimit -u 10000
module load compiler/GCC/10.2.0
module load compiler/GCCcore/10.2.0
module load lang/Python/3.8.6-GCCcore-10.2.0
module load lang/Java/16.0.1
export PATH=$PATH:$HOME/.local/bin:$HOME/bin:$HOME/deps/gecode:$HOME/deps/libminizinc/build
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$HOME/deps/gecode
source hpcpy/bin/activate

algorithms=("cusolve-mo" "solve-mo-then-uf" "solve-mo-keep-all-then-uf")
strategy="firstfail-random"
uf_strategies=("not_assignment" "decrease_hop" "forbid_source_alloc" "forbid_target_alloc")
timeout_sec=60
solvers=("gecode")
summary="summary_test.csv"


echo "Start Loop, yeay."

tasks_counter=1
for f in ../data/dzn/test/*;
do
  if [ -f $f ]
  then
    data_name=$(basename -- "$f" .dzn)
    # if [ $data_name == "topology75-14_005_c20" ]
    # then
      for algorithm in ${algorithms[@]}; do
        for uf_strategy in ${uf_strategies[@]}; do
          for solver in ${solvers[@]}; do
            res_dir="test/"$solver"_"$strategy"_"$uf_strategy"_"$algorithm"/"$data_name
            mkdir -p $res_dir
	    echo "Start srun...."$res_dir
            srun --exclusive --cpu-bind=cores -n1 -c16 python3 mo.py "$data_name" --model_mzn="../model/automotive-sat.mzn" --objectives_dzn="../model/objectives.dzn" --dzn_dir="../data/dzn" --topology_dir="../data/raw-csv" --solver_name="$solver" --timeout_sec="$timeout_sec" --results_dir="$res_dir" --bin="../bin" --summary="$summary" --uf_strategy="$uf_strategy" --cp_strategy="$strategy" --algorithm="$algorithm" | tee -a $res_dir/"output.txt" &
            [[ $((tasks_counter%64)) -eq 0 ]] && wait
            let tasks_counter++
          done
        done
      done
    # fi
  fi
done
wait
