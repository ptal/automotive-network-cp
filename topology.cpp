#include <vector>
#include <iostream>
#include <string>
#include <fstream>
#include <sstream>
#include <streambuf>
#include <map>
#include <cassert>
#include <limits>

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
vector<string> split_csv(const string& line) {
  stringstream ss(line);
  vector<string> result;
  while(ss.good())
  {
    string substr;
    getline(ss, substr, ';');
    result.push_back(substr);
  }
  return result;
}

struct LinkString {
  string from;
  string to;
  int speed;
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

class Network {
  vector<string> nodes;
  vector<string> routers;
  vector<Link> links;

  map<string, int> name2idx;
  vector<string> idx2name;

  vector<vector<int>> dist;
  vector<vector<int>> next;

public:
  Network(const vector<string>& nodes, const vector<string>& routers, const vector<LinkString>& links_str)
    : nodes(nodes), routers(routers)
  {
    for(int i = 0; i < nodes.size(); ++i) {
      name2idx[nodes[i]] = idx2name.size();
      idx2name.push_back(nodes[i]);
    }
    for(int i = 0; i < routers.size(); ++i) {
      name2idx[routers[i]] = idx2name.size();
      idx2name.push_back(routers[i]);
    }
    for(const auto& link : links_str) {
      links.push_back(Link(name2idx[link.from], name2idx[link.to], link.speed));
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
  }

  void print_input_network() const {
    for(const auto& n : nodes) { cout << n << " "; }
    cout << endl;
    for(const auto& n : routers) { cout << n << " "; }
    cout << endl;
    for(const auto& l : links) {
      cout << idx2name[l.from] << " <--" << l.speed << "--> " << idx2name[l.to] << endl;
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
    cout << "Could not find a direct edge between " << idx2name[a] << " and " << idx2name[b] << endl;
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
          cout << "No path between " << idx2name[from] << " and " << idx2name[to] << endl;
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
    cout << "num_links = " << links.size() << ";" << endl;
    cout << "capacity = [";
    for(int i = 0; i < links.size(); ++i) {
      cout << links[i].speed << (i+1 == links.size() ? "];\n" : ", ");
    }
    cout << "shortest_path = [|" << endl;
    for(int i = 0; i < dist.size(); ++i) {
      cout << "   ";
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
  Network network(nodes, routers, links);
  network.print_input_network();
  network.floyd_warshall();
  // cout << "Floyd Washall algorithm terminated." << endl;
  // network.print_floyd_matrices();
  network.build_all_shortest_paths();
  // cout << "All shortest paths construction terminated." << endl;
  network.print_dzn();
}
