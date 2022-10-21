#!/bin/sh
set -x

cd generators
g++ topology2dzn.cpp -o ../topology2dzn -std=c++20
cd ..

for f in data/raw-csv/*;
do
	./topology2dzn "$f" > "data/dzn/$(basename -- "$f" .csv).dzn"
done
