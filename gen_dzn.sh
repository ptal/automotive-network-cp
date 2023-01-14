#!/bin/sh
set -x

cd generators
g++ topology2dzn.cpp -o ../topology2dzn -std=c++20
cd ..

for f in data/raw-csv/*;
do
	./topology2dzn "$f" > "data/dzn/$(basename -- "$f" .csv)_c20.dzn" 20 constant
	./topology2dzn "$f" > "data/dzn/$(basename -- "$f" .csv)_u20.dzn" 20 uniform
	./topology2dzn "$f" > "data/dzn/$(basename -- "$f" .csv)_n20.dzn" 20 normal

	./topology2dzn "$f" > "data/dzn/$(basename -- "$f" .csv)_c40.dzn" 40 constant
	./topology2dzn "$f" > "data/dzn/$(basename -- "$f" .csv)_u40.dzn" 40 uniform
	./topology2dzn "$f" > "data/dzn/$(basename -- "$f" .csv)_n40.dzn" 40 normal

	./topology2dzn "$f" > "data/dzn/$(basename -- "$f" .csv)_c60.dzn" 60 constant
	./topology2dzn "$f" > "data/dzn/$(basename -- "$f" .csv)_u60.dzn" 60 uniform
	./topology2dzn "$f" > "data/dzn/$(basename -- "$f" .csv)_n60.dzn" 60 normal

	./topology2dzn "$f" > "data/dzn/$(basename -- "$f" .csv)_c80.dzn" 80 constant
	./topology2dzn "$f" > "data/dzn/$(basename -- "$f" .csv)_u80.dzn" 80 uniform
	./topology2dzn "$f" > "data/dzn/$(basename -- "$f" .csv)_n80.dzn" 80 normal

	./topology2dzn "$f" > "data/dzn/$(basename -- "$f" .csv)_c90.dzn" 90 constant
	./topology2dzn "$f" > "data/dzn/$(basename -- "$f" .csv)_u90.dzn" 90 uniform
	./topology2dzn "$f" > "data/dzn/$(basename -- "$f" .csv)_n90.dzn" 90 normal

	./topology2dzn "$f" > "data/dzn/$(basename -- "$f" .csv)_c100.dzn" 100 constant
	./topology2dzn "$f" > "data/dzn/$(basename -- "$f" .csv)_u100.dzn" 100 uniform
	./topology2dzn "$f" > "data/dzn/$(basename -- "$f" .csv)_n100.dzn" 100 normal
done
