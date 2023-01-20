#!/bin/bash -l
#SBATCH --account=p200021
#SBATCH --time=00:05:00
#SBATCH --partition=batch
#SBATCH --nodes=8
#SBATCH --exclusive
#SBATCH --mem=0
#SBATCH --ntasks-per-node=8
#SBATCH --cpus-per-task=16

ulimit -u 10000

# Note: all tasks take the same time, so it should be fine to use this method.
TASK=run_stressme
ncores=${SLURM_NTASKS_PER_NODE:-$(nproc --all)}
For i in {1..30}; do
    srun ${TASK} $i &
    [[ $((i%ncores)) -eq 0 ]] && wait
done
wait

algorithms=("cusolve-mo" "solve-mo-then-uf" "solve-mo-keep-all-then-uf")
strategy=firstfail-random
uf_strategies=("not_assignment" "decrease_hop" "forbid_source_alloc" "forbid_target_alloc")
timeout_sec=60
solvers=("gecode")
summary="summary_test.csv"

tasks=0
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
            srun python3 mo.py "$data_name" --model_mzn="../model/automotive-sat.mzn" --objectives_dzn="../model/objectives.dzn" --dzn_dir="../data/dzn" --topology_dir="../data/raw-csv" --solver_name="$solver" --timeout_sec="$timeout_sec" --results_dir="$res_dir" --bin="../bin" --summary="$summary" --uf_strategy="$uf_strategy" --cp_strategy="$strategy" --algorithm="$algorithm" | tee -a $res_dir/"output.txt" &
            [[ $((tasks%64)) -eq 0 ]] && wait
            let tasks++
          done
        done
      done
    # fi
  fi
done

