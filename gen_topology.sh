#!/bin/sh
set -x

cd generators
g++ dzn2topology.cpp -o ../dzn2topology -std=c++20
cd ..

for f in data/dzn/*;
do
  if [ -f $f ]
  then
      ./dzn2topology "data/raw-csv/$(basename -- "$f" .dzn).csv" "results/dzn/cpu-60-percent/3600s-$(basename -- "$f")" > "results/raw-csv/cpu-60-percent/$(basename -- "$f" .dzn).csv"
      ./dzn2topology "data/raw-csv/$(basename -- "$f" .dzn).csv" "results/dzn/cpu-80-percent/60s-$(basename -- "$f")" > "results/raw-csv/cpu-80-percent/$(basename -- "$f" .dzn).csv"
  fi
done
