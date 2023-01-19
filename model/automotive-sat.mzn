include "globals.mzn";

int: locations;
set of int: LOCATIONS = 1..locations;
array[LOCATIONS] of int: cpu_capacity;
array[LOCATIONS] of var int: cpu_usage;

int: services;
set of int: SERVICES = 1..services;
array[SERVICES] of var LOCATIONS: services2locs;
array[SERVICES] of int: services_cpu_usage;
array[SERVICES, SERVICES] of int: coms; % communication

array[LOCATIONS] of string: locations2names;
array[SERVICES] of string: services2names;

% CPU load constraint: do not exceed the capacity of each CPU.
constraint forall(l in LOCATIONS)
                 (cpu_usage[l] =
                    sum(s in SERVICES)
                       (services_cpu_usage[s] * (services2locs[s] == l)));
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

array[1..3] of var int: objs;
constraint objs[1] = max(link in NUM_LINKS)(charge[link]);
constraint objs[2] = max(l in LOCATIONS)(cpu_usage[l]);
constraint objs[3] = sum(l in LOCATIONS)(cpu_usage[l] == 0);

array[1..3] of bool: minimize_objs;
array[1..3] of int: ref_point;

solve
 :: int_search(services2locs, first_fail, indomain_random)
%solve :: int_search(services2locs, first_fail, indomain_min)
%solve :: int_search(services2locs, dom_w_deg, indomain_random)
satisfy;
