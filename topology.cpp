#include <vector>
#include <iostream>
#include <string>
#include <fstream>
#include <sstream>
#include <streambuf>
#include <map>
#include <cassert>

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

struct Link {
  string from;
  string to;
  int speed;
  Link(const string& from, const string& to, int speed):
    from(from), to(to), speed(speed) {}
};

class Network {
  vector<string> nodes;
  vector<string> routers;
  vector<Link> links;

  map<string, int> name2idx;
  vector<string> idx2name;

public:
  Network(const vector<string>& nodes, const vector<string>& routers, const vector<Link>& links)
    : nodes(nodes), routers(routers), links(links)
  {
    for(int i = 0; i < nodes.size(); ++i) {
      name2idx[nodes[i]] = idx2name.size();
      idx2name.push_back(nodes[i]);
    }
    for(int i = 0; i < routers.size(); ++i) {
      name2idx[routers[i]] = idx2name.size();
      idx2name.push_back(routers[i]);
    }
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
  for(const auto& n : nodes) { cout << n << " "; }
  cout << endl;
  read_until(t, "[Routers]");
  read_line(t);
  vector<string> routers = read_until(t, "[Wired Links]");
  for(auto& router : routers) {
    router = split_csv(router)[0];
  }
  read_line(t);
  vector<Link> links;
  for(const auto& link : read_until(t, "[GenericSyncConfig];[ClockPrecision];[ClockConfig]")) {
    auto csv_line = split_csv(link);
    links.push_back(Link(csv_line[1], csv_line[3], stoi(csv_line[5])));
  }
  for(const auto& n : routers) {
    cout << n << " ";
  }
  cout << endl;
  for(const auto& l : links) {
    cout << l.from << " <--" << l.speed << "--> " << l.to << endl;
  }
  cout << endl;
}
