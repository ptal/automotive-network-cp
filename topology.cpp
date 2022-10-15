#include <vector>
#include <iostream>
#include <string>
#include <fstream>
#include <sstream>
#include <streambuf>
#include <map>
#include <cassert>
#include <limits>
#include <iterator>
#include <algorithm>

using namespace std;

string read_line(ifstream& t) {
  string line;
  bool read = static_cast<bool>(getline(t, line));
  assert(read);
  return std::move(line);
}

vector<string> read_until(ifstream& t, const string& last) {
  string line;
  vector<string> res;
  while(getline(t, line) && line != last) {
    res.push_back(std::move(line));
  }
  assert(line == last);
  return res;
}

// https://stackoverflow.com/a/10861816/2231159
vector<string> split_on(const string& line, char delim) {
  stringstream ss(line);
  vector<string> result;
  while(ss.good())
  {
    string substr;
    getline(ss, substr, delim);
    result.push_back(substr);
  }
  return result;
}

vector<string> split_csv(const string& line) {
  return split_on(line, ';');
}

struct LinkString {
  string from;
  string to;
  int speed; // Speed of the link in Mbit/sec
  LinkString(const string& from, const string& to, int speed):
    from(from), to(to), speed(speed) {}
};

struct Link {
  int from;
  int to;
  int speed;
  Link(int from, int to, int speed):
    from(from), to(to), speed(speed) {}
};

struct ServiceComString {
  string service;
  string from;
  string to;

  int speed; // The number of bits per second that the service sends.

  ServiceComString(const string& service, const string& from, const string& to, int speed):
    service(service), from(from), to(to), speed(speed) {}
};

struct ServiceCom {
  int from;
  vector<int> to;
  vector<int> speed; // The number of bits per second that the service sends.

  ServiceCom(int from): from(from) {}
};

class Network {
  vector<string> nodes;
  vector<string> routers;
  vector<Link> links;

  map<string, int> node2idx;
  vector<string> idx2node;

  vector<vector<int>> dist;
  vector<vector<int>> next;

  map<string, int> service2idx;
  vector<string> idx2service;
  vector<vector<int>> coms; // The speed in bits / second required between each service communication.


  void initialize_communications(const vector<ServiceComString>& raw_coms) {
    vector<ServiceCom> services;
    // For each processor, provide the list of services allocated (by default) on it.
    // Although that shouldn't be possible, the topology files currently give a service that is allocated on several processors.
    vector<vector<int>> procs(idx2node.size());
    for(const auto& com : raw_coms) {
      if(!service2idx.contains(com.service)) {
        int service_idx = idx2service.size();
        service2idx[com.service] = service_idx;
        idx2service.push_back(com.service);
        services.push_back(ServiceCom(service_idx));
      }
      int service_idx = service2idx[com.service];
      services[service_idx].to.push_back(node2idx[com.to]);
      services[service_idx].speed.push_back(com.speed);
      auto& services_on_proc = procs[node2idx[com.from]];
      if(ranges::find(services_on_proc, service_idx) == services_on_proc.end()) {
        services_on_proc.push_back(service_idx);
      }
    }
    vector<int> next_service_on_proc(services.size(), 0);
    coms.resize(services.size());
    for(int i = 0; i < services.size(); ++i) {
      coms[i].assign(services.size(), 0);
    }
    for(const auto& s : services) {
      for(int j = 0; j < s.to.size(); ++j) {
        int nodeIdx = s.to[j];
        int randomService = procs[nodeIdx][next_service_on_proc[nodeIdx] % procs[nodeIdx].size()];
        next_service_on_proc[nodeIdx]++;
        coms[s.from][randomService] = s.speed[j];
      }
    }
  }

public:
  Network(const vector<string>& nodes, const vector<string>& routers, const vector<LinkString>& links_str,
    const vector<ServiceComString>& raw_coms)
    : nodes(nodes), routers(routers)
  {
    for(int i = 0; i < nodes.size(); ++i) {
      node2idx[nodes[i]] = idx2node.size();
      idx2node.push_back(nodes[i]);
    }
    for(int i = 0; i < routers.size(); ++i) {
      node2idx[routers[i]] = idx2node.size();
      idx2node.push_back(routers[i]);
    }
    for(const auto& link : links_str) {
      links.push_back(Link(node2idx[link.from], node2idx[link.to], link.speed));
    }
    dist.resize(nodes.size() + routers.size());
    next.resize(nodes.size() + routers.size());
    for(int i = 0; i < dist.size(); ++i) {
      dist[i].resize(dist.size());
      next[i].resize(next.size());
      for(int j = 0; j < dist.size(); ++j) {
        dist[i][j] = numeric_limits<int>::max() / 10;
        next[i][j] = -1;
      }
    }
    initialize_communications(raw_coms);
  }

  void print_input_network() const {
    for(const auto& n : nodes) { cout << n << " "; }
    cout << endl;
    for(const auto& n : routers) { cout << n << " "; }
    cout << endl;
    for(const auto& l : links) {
      cout << idx2node[l.from] << " <--" << l.speed << "--> " << idx2node[l.to] << endl;
    }
  }

  void floyd_warshall() {
    for(int i = 0; i < links.size(); ++i) {
      dist[links[i].from][links[i].to] = 1;
      dist[links[i].to][links[i].from] = 1;
      next[links[i].from][links[i].to] = links[i].to;
      next[links[i].to][links[i].from] = links[i].from;
    }
    for(int i = 0; i < dist.size(); ++i) {
      dist[i][i] = 0;
      next[i][i] = i;
    }
    for(int k = 0; k < dist.size(); ++k) {
      for(int i = 0; i < dist.size(); ++i) {
        for(int j = 0; j < dist.size(); ++j) {
          if(dist[i][j] > dist[i][k] + dist[k][j]) {
            dist[i][j] = dist[i][k] + dist[k][j];
            next[i][j] = next[i][k];
          }
        }
      }
    }
  }

  void print_floyd_matrices() const {
    for(int i = 0; i < dist.size(); ++i) {
      for(int j = 0; j < dist.size(); ++j) {
        cout << dist[i][j] << " ";
      }
      cout << endl;
    }
    for(int i = 0; i < dist.size(); ++i) {
      for(int j = 0; j < dist.size(); ++j) {
        cout << next[i][j] << " ";
      }
      cout << endl;
    }
  }

  // `all_shortest_paths[a][b]` contains the shortest path between `a` to `b`.
  // The shortest path is expressed as a list of edge indices.
  vector<vector<vector<int>>> all_shortest_paths;

  int edge_id(int a, int b) {
    for(int i = 0; i < links.size(); ++i) {
      if((links[i].to == a && links[i].from == b) ||
         (links[i].from == a && links[i].to == b))
      {
        return i;
      }
    }
    cout << "Could not find a direct edge between " << idx2node[a] << " and " << idx2node[b] << endl;
    return -10;
  }

  void build_all_shortest_paths() {
    all_shortest_paths.resize(dist.size());
    for(int from = 0; from < dist.size(); ++from) {
      all_shortest_paths[from].resize(dist.size());
      for(int to = 0; to < dist.size(); ++to) {
        if(next[from][to] != -1) {
          int u = from;
          while(u != to) {
            int n = next[u][to];
            all_shortest_paths[from][to].push_back(edge_id(u, n));
            u = n;
          }
        }
        else if(from != to) {
          cout << "No path between " << idx2node[from] << " and " << idx2node[to] << endl;
        }
      }
    }
  }

  void print_dzn() const {
    cout << "locations = " << dist.size() << ";" << endl;
    cout << "cpu_capacity = [";
    for(int i = 0; i < dist.size(); ++i) {
      if(i >= nodes.size()) {
        cout << "0"; // All switches have a CPU capacity of 0.
      }
      else {
        cout << "100";
      }
      cout << (i+1 == dist.size() ? "];\n" : ", ");
    }
    cout << "cpu_service = [";
    for(int i = 0; i < idx2service.size(); ++i) {
      cout << "20";
      cout << (i+1 == idx2service.size() ? "];\n" : ", ");
    }
    cout << "services = " << service2idx.size() << ";" << endl;
    cout << "coms = [|" << endl;
    for(int i = 0; i < coms.size(); ++i) {
      cout << "   " << ((i > 0) ? "|" : "");
      for(int j = 0; j < coms.size(); ++j) {
        cout << coms[i][j] << ((i+1 == coms.size() && j+1 == coms.size()) ? "" : ",");
      }
      cout << endl;
    }
    cout << "|];" << endl;
    cout << "num_links = " << links.size() << ";" << endl;
    cout << "capacity = [";
    for(int i = 0; i < links.size(); ++i) {
      cout << links[i].speed * 1000 * 1000 << (i+1 == links.size() ? "];\n" : ", ");
    }
    cout << "shortest_path = [|" << endl;
    for(int i = 0; i < dist.size(); ++i) {
      cout << "   " << ((i > 0) ? "|" : "");
      for(int j = 0; j < dist.size(); ++j) {
        cout << "{";
        for(int k = 0; k < all_shortest_paths[i][j].size(); ++k) {
          cout << all_shortest_paths[i][j][k]+1;
          if(k+1 != all_shortest_paths[i][j].size()) {
            cout << ", ";
          }
        }
        cout << "}";
        if(j + 1 == dist.size()) {
          if(i + 1 != dist.size()) {
            cout << ",\n";
          }
        }
        else {
          cout << ", ";
        }
      }
    }
    cout << "|];" << endl;
  }
};

int main(int argc, char** argv) {
  if(argc != 2) {
    cout << "usage: " << argv[0] << " <network-topology.csv>";
  }
  ifstream t(argv[1]);
  read_until(t, "[Nodes]");
  read_until(t, "[Name]");
  vector<string> nodes = read_until(t, "[EthernetTopology]");
  read_until(t, "[Routers]");
  read_line(t);
  vector<string> routers = read_until(t, "[Wired Links]");
  for(auto& router : routers) {
    router = split_csv(router)[0];
  }
  read_line(t);
  vector<LinkString> links;
  for(const auto& link : read_until(t, "[GenericSyncConfig];[ClockPrecision];[ClockConfig]")) {
    auto csv_line = split_csv(link);
    links.push_back(LinkString(csv_line[1], csv_line[3], stoi(csv_line[5])));
  }
  read_until(t, "[Frames]");
  read_line(t);
  vector<ServiceComString> coms;
  for(const auto& com : read_until(t, "[EthernetRouting]")) {
    auto csv_line = split_csv(com);
    auto service_name = split_on(csv_line[0], '_')[0];
    int data = stoi(csv_line[8]);
    bool burst = csv_line[3] == "PeriodicBursts";
    if(burst) {
      data *= stoi(csv_line[9]);
    }
    int freq = (int)(1000.0 / stod(csv_line[4]));
    coms.push_back(ServiceComString(service_name, csv_line[10], csv_line[12], data * freq * 8));
  }
  Network network(nodes, routers, links, coms);
  network.print_input_network();
  network.floyd_warshall();
  // cout << "Floyd Washall algorithm terminated." << endl;
  // network.print_floyd_matrices();
  network.build_all_shortest_paths();
  // cout << "All shortest paths construction terminated." << endl;
  network.print_dzn();
}
