include "globals.mzn";

int: locations;
set of int: LOCATIONS = 1..locations;
array[LOCATIONS] of int: cpu_capacity;
array[LOCATIONS] of var int: cpu_usage;

int: services;
set of int: SERVICES = 1..services;
array[SERVICES] of var LOCATIONS: services2locs;
array[SERVICES] of int: cpu_service;
array[SERVICES, SERVICES] of int: coms; % communication

array[LOCATIONS] of string: locations2names;
array[SERVICES] of string: services2names;

% CPU load constraint: do not exceed the capacity of each CPU.
constraint forall(l in LOCATIONS)
                 (cpu_usage[l] =
                    sum(s in SERVICES)
                       (cpu_service[s] * (services2locs[s] == l)));
constraint forall(l in LOCATIONS)(cpu_usage[l] >= 0 /\ cpu_usage[l] <= cpu_capacity[l]);

int: num_links;
set of int: NUM_LINKS = 1..num_links;
% array[NUM_LINKS] of int: from;
% array[NUM_LINKS] of int: to;
array[NUM_LINKS] of int: capacity;
array[NUM_LINKS] of var int: slack;

% `shortest_path[a, b]` contains all the edges belonging to the shortest path between `a` to `b`.
array[LOCATIONS, LOCATIONS] of set of NUM_LINKS: shortest_path;

% Network load constraint: for each network link, its occupancy by services' communications should not exceed its capacity.
% We first compute the slack of each link.
constraint forall(link in NUM_LINKS)(
            slack[link] = capacity[link] -
              sum(s1,s2 in SERVICES)(
                coms[s1,s2] * (link in shortest_path[services2locs[s1], services2locs[s2]])
              ));

% Then we ensure the slack is always greater or equal to 0.
constraint forall(link in NUM_LINKS)(slack[link] >= 0 /\ slack[link] <= capacity[link]);

array[NUM_LINKS] of var 0..100: charge;
constraint forall(link in NUM_LINKS)(charge[link] == (capacity[link] - slack[link]) div (capacity[link] div 100));

% var int: w = min(link in NUM_LINKS)(slack[link] div 100) * min(l in LOCATIONS)((100-cpu_usage[l]));
var int: w1 = max(link in NUM_LINKS)(charge[link]);
var int: w2 = max(l in LOCATIONS)(cpu_usage[l]);
var int: w = w1 * w2;
 solve :: int_search(services2locs, first_fail, indomain_random)
% solve :: int_search(services2locs, first_fail, indomain_min)
%solve :: int_search(services2locs, dom_w_deg, indomain_random)
minimize w;

output
  ["w = \(w); \n"] ++
  ["link_objective = \(w1); \n"] ++
  ["cpu_objective = \(w2); \n"] ++
  ["services2locs = \(services2locs);\n"] ++
  ["locations2names = \(locations2names);\n"] ++
  ["services2names = \(services2names);\n"] ++
  ["cpu_usage = \(cpu_usage); \n"] ++
  ["slack = \(slack); \n"] ++
  ["charge = \(charge); \n"];
