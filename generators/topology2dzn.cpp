// Copyright 2022 Pierre Talbot


#include "utility.hpp"
#include "topology.hpp"

using namespace std;

int main(int argc, char** argv) {
  if(argc != 4) {
    cout << "usage: " << argv[0] << " <network-topology.csv> <cpu_occupancy> <occupancy_distribution>";
  }
  Network network = read_network(argv[1]);
  network.generate_services_cpu_usage(stoi(argv[2]), argv[3]);
  network.print_dzn();
}
