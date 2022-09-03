include "globals.mzn";

int: locations;
set of int: LOCATIONS = 1..locations;
array[LOCATIONS] of int: cpu_capacity;
array[LOCATIONS] of var int: cpu_usage;

int: services;
set of int: SERVICES = 1..services;
array[SERVICES] of var int: services2locs;
array[SERVICES] of int: cpu_usages;
array[SERVICES, SERVICES] of int: services_com;

% CPU load constraint: do not exceed the capacity of each CPU.
constraint forall(l in LOCATIONS)
                 (cpu_usage[l] =
                    sum(s in SERVICES)
                       (cpu_usages[s] * (services2locs[s] == l)));
constraint forall(l in LOCATIONS)(cpu_capacity[l] >= cpu_usage[l]);

int: num_links;
set of int: NUM_LINKS = 1..num_links;
% array[NUM_LINKS] of int: from;
% array[NUM_LINKS] of int: to;
array[NUM_LINKS] of int: capacity;
array[NUM_LINKS] of var int: slack;

% `shortest_path[a, b]` contains all the edges belonging to the shortest path between `a` to `b`.
array[LOCATIONS, LOCATIONS] of NUM_LINKS: shortest_path;

% Network load constraint: for each network link, its occupancy by services' communications should not exceed its capacity.
% We first compute the slack of each link.
constraint forall(link in NUM_LINKS)(
            slack[link] = capacity[link] -
              sum(s1,s2 in SERVICES)(
                services_com[s1,s2] * (link in shortest_path[services2locs[s1], services2locs[s2]])
              ));

% Then we ensure the slack is always greater or equal to 0.
constraint forall(link in NUM_LINKS)(slack[link] >= 0);

% Note that the objectives should be normalized using weight.
solve maximize (min(link in NUM_LINKS)(slack[link])
              + min(l in LOCATIONS)(cpu_usage[l]));
