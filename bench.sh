#!/bin/sh
set -x

cd generators
g++ dzn2topology.cpp -o ../dzn2topology -std=c++20
cd ..

for f in data/dzn/*;
do
  if [ -f $f ]
  then
    minizinc -s --compiler-statistics -O3 --allow-unbounded-vars --solver org.gecode.gecode --time-limit 3600000 model/automotive.mzn "$f" > "results/dzn/3600s-$(basename -- "$f")"
    ./dzn2topology "data/raw-csv/$(basename -- "$f" .dzn).csv" "results/dzn/$(basename -- "$f")" > "results/raw-csv/$(basename -- "$f" .dzn).csv"
  fi
done
