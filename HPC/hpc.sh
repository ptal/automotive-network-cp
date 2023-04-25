#!/bin/bash -l
#SBATCH --time=36:00:00
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
source ../mo-mzn/hpcpy/bin/activate

cd ../minizinc-mo
cp_strategy="firstfail-random"
uf_conflict_strategies=("not_assignment" "decrease_one_link_charge" "decrease_max_link_charge" "forbid_source_alloc" "forbid_target_alloc" "forbid_source_target_alloc_or" "forbid_source_target_alloc_and" "decrease_hop_or" "decrease_hop_and")
uf_conflict_combinators=("and" "or")
cp_timeout_sec=1800
solver="gecode"
summary="../results/summary_hpc.csv"
res_dir="../results"

echo "Start Loop, yeay."

cores=16
tasks_counter=1
algorithm="cusolve-mo"
for f in ../data/dzn/*005_u*.dzn;
do
  if [ -f $f ]
  then
    data_name=$(basename -- "$f" .dzn)
    for uf_conflict_strategy in ${uf_conflict_strategies[@]}; do
      for uf_conflict_combinator in ${uf_conflict_combinators[@]}; do
        log_file=$res_dir"/"$cp_strategy"_"$uf_conflict_strategy"_"$uf_conflict_combinator"_"$algorithm"_"$cp_timeout_sec"_"$data_name
        echo "Start srun...."$res_dir
        srun --exclusive --cpu-bind=cores -n1 -c $cores python3 main.py --cores $cores --model_mzn "../model/automotive-sat.mzn" --objectives_dzn "../model/objectives.dzn" --dzn_dir "../data/dzn/" --topology_dir "../data/raw-csv" --solver_name "$solver" --cp_timeout_sec $cp_timeout_sec --tmp_dir "$res_dir" --bin "../bin" --summary "$summary" --uf_conflict_strategy "$uf_conflict_strategy" --uf_conflicts_combinator "$uf_conflict_combinator" --cp_strategy="$cp_strategy" --fzn_optimisation_level 1 --algorithm "$algorithm" "$data_name" 2>&1 | tee -a "$log_file" &
        [[ $((tasks_counter%64)) -eq 0 ]] && wait
        let tasks_counter++
      done
    done
  fi
done

algorithm="osolve-mo-then-uf"
for f in ../data/dzn/*005_u*.dzn;
do
  if [ -f $f ]
  then
    data_name=$(basename -- "$f" .dzn)
    log_file=$res_dir"/"$cp_strategy"_"$algorithm"_"$cp_timeout_sec"_"$data_name
    echo "Start srun...."$res_dir
    srun --exclusive --cpu-bind=cores -n1 -c $cores python3 main.py --cores $cores --model_mzn "../model/automotive-sat.mzn" --objectives_dzn "../model/objectives.dzn" --dzn_dir "../data/dzn/" --topology_dir "../data/raw-csv" --solver_name "$solver" --cp_timeout_sec $cp_timeout_sec --tmp_dir "$res_dir" --bin "../bin" --summary "$summary" --uf_conflict_strategy "na" --uf_conflicts_combinator "na" --cp_strategy="$cp_strategy" --fzn_optimisation_level 1 --algorithm "$algorithm" "$data_name" 2>&1 | tee -a $res_dir/"output.txt" &
    [[ $((tasks_counter%64)) -eq 0 ]] && wait
    let tasks_counter++
  fi
done
wait
