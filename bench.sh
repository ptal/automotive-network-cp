#!/bin/sh
set -x

cd generators
g++ dzn2topology.cpp -o ../dzn2topology -std=c++20
cd ..

for f in data/dzn/*;
do
  minizinc -s --compiler-statistics -O3 --allow-unbounded-vars --solver org.gecode.gecode --time-limit 60000 model/automotive.mzn "$f" > "results/dzn/$(basename -- "$f")"
  ./dzn2topology "data/raw-csv/$(basename -- "$f" .dzn).csv" "results/dzn/$(basename -- "$f")" > "results/raw-csv/$(basename -- "$f" .dzn).csv"
done
