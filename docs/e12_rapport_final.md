# E12 — rapport final (sortie du gabarit gelé, commit 0fa5787)

```
[e12] test_results.json written; policy / script / dm_reward / dm_cost / matched_cost / coverage
c40f2fe7  always_rr            7.027 0.0287 [0.0258,0.0319] 0.0216 cov 45.3%
c40f2fe7  always_pf            6.688 0.1294 [0.1188,0.1400] 0.0664 cov 54.7%
c40f2fe7  best_fixed           2.734 0.0140 [0.0125,0.0156] 0.0308 cov 13.0%
c40f2fe7  table_greedy         9.069 0.0217 [0.0204,0.0230] 0.0310 cov 9.5%
c40f2fe7  safe_cql_a0.1        6.968 0.0315 [0.0290,0.0344] 0.0274 cov 35.0%
c40f2fe7  cql_a0.1             7.117 0.0551 [0.0491,0.0612] 0.0415 cov 36.0%
c40f2fe7  safe_cql_a0.5        6.776 0.0305 [0.0272,0.0342] 0.0357 cov 34.8%
c40f2fe7  cql_a0.5             6.733 0.0548 [0.0486,0.0609] 0.0436 cov 39.4%
c40f2fe7  safe_cql_a0.1_g0     6.773 0.0286 [0.0253,0.0325] 0.0342 cov 33.5%
c40f2fe7  iql                  6.787 0.0582 [0.0516,0.0649] 0.0452 cov 40.3%
1dd38082  always_rr            9.813 0.0296 [0.0263,0.0327] 0.0104 cov 66.0%
1dd38082  always_pf            9.870 0.1616 [0.1323,0.1803] 0.0606 cov 34.0%
1dd38082  best_fixed           3.352 0.0211 [0.0157,0.0234] nan cov 0.0%
1dd38082  table_greedy        10.940 0.0266 [0.0262,0.0274] 0.0017 cov 18.0%
1dd38082  safe_cql_a0.1        9.898 0.0280 [0.0258,0.0303] 0.0110 cov 34.9%
1dd38082  cql_a0.1            10.111 0.0485 [0.0364,0.0633] 0.0175 cov 34.5%
1dd38082  safe_cql_a0.5        9.616 0.0259 [0.0239,0.0277] 0.0083 cov 34.2%
1dd38082  cql_a0.5             9.659 0.0510 [0.0395,0.0625] 0.0179 cov 41.9%
1dd38082  safe_cql_a0.1_g0     9.635 0.0257 [0.0237,0.0276] 0.0099 cov 28.9%
1dd38082  iql                  9.760 0.0595 [0.0413,0.0826] 0.0159 cov 37.2%
3e1a4369  always_rr            7.804 0.0241 [0.0108,0.0374] 0.0045 cov 100.0%
3e1a4369  always_pf            7.283 0.0541 [0.0507,0.0579] nan cov 0.0%
3e1a4369  best_fixed           2.810 0.0031 [0.0028,0.0033] nan cov 0.0%
3e1a4369  table_greedy         8.477 0.0259 [0.0206,0.0293] 0.0136 cov 1.2%
3e1a4369  safe_cql_a0.1        7.984 0.0247 [0.0199,0.0289] 0.0069 cov 57.4%
3e1a4369  cql_a0.1             8.451 0.0338 [0.0282,0.0394] 0.0069 cov 47.7%
3e1a4369  safe_cql_a0.5        7.408 0.0165 [0.0109,0.0228] 0.0058 cov 67.5%
3e1a4369  cql_a0.5             8.046 0.0299 [0.0250,0.0355] 0.0073 cov 50.3%
3e1a4369  safe_cql_a0.1_g0     7.286 0.0156 [0.0104,0.0216] 0.0059 cov 69.7%
3e1a4369  iql                  8.055 0.0323 [0.0255,0.0386] 0.0089 cov 43.8%
pooled    always_rr            7.211 0.0285 [0.0258,0.0314] 0.0191 cov 49.1%
pooled    always_pf            6.883 0.1272 [0.1168,0.1368] 0.0662 cov 50.9%
pooled    best_fixed           2.769 0.0138 [0.0124,0.0152] 0.0308 cov 11.7%
pooled    table_greedy         9.135 0.0222 [0.0209,0.0233] 0.0280 cov 9.5%
pooled    safe_cql_a0.1        7.172 0.0310 [0.0288,0.0335] 0.0249 cov 36.1%
pooled    cql_a0.1             7.340 0.0536 [0.0483,0.0593] 0.0380 cov 36.5%
pooled    safe_cql_a0.5        6.955 0.0295 [0.0266,0.0327] 0.0315 cov 36.4%
pooled    cql_a0.5             6.951 0.0533 [0.0476,0.0589] 0.0399 cov 40.1%
pooled    safe_cql_a0.1_g0     6.947 0.0278 [0.0248,0.0310] 0.0303 cov 35.1%
pooled    iql                  7.005 0.0569 [0.0512,0.0630] 0.0418 cov 40.3%
{
 "c40f2fe7": {
  "a": {
   "table_greedy_above_all_agents": true,
   "agents_close": true,
   "holds": true
  },
  "b": {
   "safe_below_cql_and_iql": true,
   "safe_ci_hi_not_below_d": true,
   "holds": true
  },
  "c": {
   "matched_same_order": true,
   "coverage_partial": true,
   "holds": true
  },
  "d": {
   "net_improvement": false,
   "cost_g0_minus_g07": -0.002885312378402328,
   "reward_g0_minus_g07": -0.19530482325791354,
   "holds": true
  },
  "e": {
   "demonstrated_safe": {
    "safe_cql_a0.1": false,
    "cql_a0.1": false,
    "safe_cql_a0.5": false,
    "cql_a0.5": false,
    "safe_cql_a0.1_g0": false,
    "iql": false,
    "always_rr": false,
    "always_pf": false,
    "best_fixed": false,
    "table_greedy": false
   },
   "holds": true
  }
 },
 "pooled": {
  "a": {
   "table_greedy_above_all_agents": true,
   "agents_close": true,
   "holds": true
  },
  "b": {
   "safe_below_cql_and_iql": true,
   "safe_ci_hi_not_below_d": true,
   "holds": true
  },
  "c": {
   "matched_same_order": true,
   "coverage_partial": true,
   "holds": true
  },
  "d": {
   "net_improvement": true,
   "cost_g0_minus_g07": -0.0031703444368750278,
   "reward_g0_minus_g07": -0.2244908251204638,
   "holds": false
  },
  "e": {
   "demonstrated_safe": {
    "safe_cql_a0.1": false,
    "cql_a0.1": false,
    "safe_cql_a0.5": false,
    "cql_a0.5": false,
    "safe_cql_a0.1_g0": false,
    "iql": false,
    "always_rr": false,
    "always_pf": false,
    "best_fixed": false,
    "table_greedy": false
   },
   "holds": true
  }
 }
}
```
