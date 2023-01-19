// Copyright 2022 Pierre Talbot

#ifndef UTILITY_HPP
#define UTILITY_HPP

#include <vector>
#include <iostream>
#include <string>
#include <fstream>
#include <istream>
#include <sstream>
#include <streambuf>
#include <regex>
#include <cassert>

using namespace std;

/** Open and read a file named `filename` and convert all line break into Unix style line breaks. */
string read_file(const char* filename) {
  ifstream t(filename);
  string raw_text((istreambuf_iterator<char>(t)), istreambuf_iterator<char>());
  string unix_file(regex_replace(raw_text, regex("\\r\\n"), "\n"));
  return unix_file;
}

string read_line(istream& t) {
  string line;
  bool read = static_cast<bool>(getline(t, line));
  assert(read);
  return std::move(line);
}

void echo_line(istream& t) {
  cout << read_line(t) << endl;
}

vector<string> read_until(istream& t, const string& last, bool echo=false) {
  string line;
  vector<string> res;
  while(getline(t, line) && line != last) {
    if(echo) {
      cout << line << endl;
    }
    res.push_back(std::move(line));
  }
  if(line != last) {
    cerr << line << endl;
    cerr << last << endl;
    assert(false);
  }
  return res;
}

void echo_until(istream& t, const string& last) {
  read_until(t, last, true);
  cout << last << endl;
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

vector<string> parse_dzn_array(const string& line) {
  istringstream s(line);
  int b = 0;
  int len = 0;
  while(line[b] != '[') { ++b; }
  ++b;
  while(line[b+len] != ']') { ++len; }
  vector<string> result = split_on(line.substr(b, len), ',');
  vector<string> cleaned;
  for(auto& s : result) {
    string s2;
    for(char c : s) {
      if(c != ' ') { s2.push_back(c); }
    }
    cleaned.push_back(s2);
  }
  return cleaned;
}

vector<string> parse_dzn_string_array(const string& line) {
  vector<string> strings = parse_dzn_array(line);
  for(auto& name : strings) {
    name = name.substr(1,name.size()-2);
  }
  return strings;
}


vector<int> parse_dzn_int_array(const string& line) {
  vector<string> strings = parse_dzn_array(line);
  vector<int> data;
  for(auto& name : strings) {
    data.push_back(stoi(name));
  }
  return data;
}


#endif
