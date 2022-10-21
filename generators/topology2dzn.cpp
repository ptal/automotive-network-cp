// Copyright 2022 Pierre Talbot


#include "utility.hpp"
#include "topology.hpp"

using namespace std;

int main(int argc, char** argv) {
  if(argc != 2) {
    cout << "usage: " << argv[0] << " <network-topology.csv>";
  }
  Network network = read_network(argv[1]);
  network.print_dzn();
}
