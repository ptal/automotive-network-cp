// Copyright 2022 Pierre Talbot

#include "utility.hpp"
#include "topology.hpp"
#include <set>

int main(int argc, char** argv) {
  if(argc != 3) {
    cout << "usage: " << argv[0] << " <network-topology.csv> <solving-output.dzn>";
  }
  Network network = read_network(argv[1]);
  istringstream t(read_file(argv[1]));
  istringstream result(read_file(argv[2]));
  string s;
  vector<int> services2locs;
  vector<string> services2names;
  map<string, int> names2services;
  vector<string> locations2names;
  map<string, int> names2locations;
  while(getline(result, s)) {
    if(s[0] != '%') {
      auto dzn_entry = split_on(s, '=');
      auto name = dzn_entry[0];
      if(name.find("services2locs") != string::npos) {
        services2locs = parse_dzn_int_array(dzn_entry[1]);
        // Decrease to be 0-indexed.
        for(int& i : services2locs) {
          --i;
        }
      }
      else if(name.find("services2names") != string::npos) {
        services2names = parse_dzn_string_array(dzn_entry[1]);
        for(int i = 0; i < services2names.size(); ++i) {
          names2services[services2names[i]] = i;
        }
      }
      else if(name.find("locations2names") != string::npos) {
        locations2names = parse_dzn_string_array(dzn_entry[1]);
        for(int i = 0; i < locations2names.size(); ++i) {
          names2locations[locations2names[i]] = i;
        }
      }
    }
  }
  echo_until(t, "[Frames]");
  echo_line(t);
  vector<pair<string, pair<string,string>>> routes;
  set<tuple<string, string, string>> frames_set; // service, source, target.
  int com_no = 0;
  for(const auto& com : read_until(t, "[EthernetRouting]")) {
    auto csv_line = split_csv(com);
    auto service_name = csv_line[0];
    csv_line[10] = locations2names[services2locs[names2services[service_name]]];
    csv_line[12] = locations2names[services2locs[names2services[network.receiver_of_communication(com_no)]]];
    // In case the sender and receiver are on the same ECU, we do not add a line for those.
    if(csv_line[10] != csv_line[12]) {
      auto frame = std::make_tuple(csv_line[0], csv_line[10], csv_line[12]);
      if(!frames_set.contains(frame)) {
        frames_set.insert(frame);
        routes.push_back(pair(service_name, pair(csv_line[10], csv_line[12])));
        for(int i = 0; i < csv_line.size(); ++i) {
          cout << csv_line[i] << ((i+1 == csv_line.size()) ? "\n":";");
        }
      }
    }
    com_no++;
  }
  cout << "[EthernetRouting]" << endl;
  echo_until(t, "[Frames]");
  for(const auto& route : routes) {
    vector<string> path = network.routing_path(route.second.first, route.second.second);
    if(path.size() > 1) {
      cout << route.first;
      for(const auto& node : path) {
        cout << ";" << node;
      }
      cout << endl;
    }
  }
  read_until(t, "[EthernetComConfig]");
  cout << "[EthernetComConfig]" << endl;
  while(getline(t, s)) {
    cout << s << endl;
  }
  return 0;
}
