# automotive-network-cp

```
python3 -m pip install pymoo minizinc[dzn] filelock numpy
```

```
cd minizinc-mo
python3 main.py --model_mzn ../model/automotive-sat.mzn --objectives_dzn ../model/objectives.dzn --dzn_dir ../data/dzn/test --topology_dir ../data/raw-csv --solver_name gecode --timeout_sec 60 --tmp_dir /tmp --bin ../bin --summary ../results/summary.csv --uf_conflict_strategy not_assignment --uf_conflicts_combinator and --cp_strategy free --algorithm osolve-mo topology50-14_001_u20
```