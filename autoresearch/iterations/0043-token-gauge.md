# iter-0043 — per-skill token gauge (baseline snapshot)

**Status**: DATA ONLY. `scripts/skill-token-gauge.py` is a new zero-dependency
gauge (chars/4 and words*1.3 estimates, both printed — no tokenizer vendored)
covering SKILL.md + references/** for every skill under `config/skills/` and
`optional-skills/`, plus `config/skills/_shared/**/*.md`, `CLAUDE.md`, and
`AGENTS.md`. It reports current cost; it does not compare, threshold, or gate
(that's `scripts/static-ab.sh`, scoped only to the `devlyn:resolve` load set).
This is a gauge, not a redesign — no subtractive pass is proposed here.

## Baseline table (2026-07-04)

```
# tokens_c4 = chars/4, tokens_w13 = words*1.3 (both approximations; no tokenizer vendored)

SKILL                        FILE                                        ROLE        LINES   CHARS  TOK≈c/4  TOK≈w*1.3
---------------------------  ------------------------------------------  ----------  -----  ------  -------  ---------
code-health-standards        SKILL.md                                    cold_start     74    3034      758        590
code-health-standards        SUBTOTAL                                                   74    3034      758        590

code-review-standards        SKILL.md                                    cold_start     64    1849      462        354
code-review-standards        SUBTOTAL                                                   64    1849      462        354

devlyn:design-ui             SKILL.md                                    cold_start    650   34593     8648       6196
devlyn:design-ui             SUBTOTAL                                                  650   34593     8648       6196

devlyn:engines               SKILL.md                                    cold_start     33    2159      539        393
devlyn:engines               SUBTOTAL                                                   33    2159      539        393

devlyn:ideate                SKILL.md                                    cold_start    159   11886     2971       2019
devlyn:ideate                references/elicitation.md                   reference     143    9625     2406       1798
devlyn:ideate                references/from-spec-mode.md                reference      76    5719     1429        971
devlyn:ideate                references/project-mode.md                  reference      95    5753     1438       1005
devlyn:ideate                references/spec-template.md                 reference     111    6450     1612       1135
devlyn:ideate                references/templates/decision.md            reference      48    1402      350        263
devlyn:ideate                references/templates/roadmap.md             reference      50    2016      504        386
devlyn:ideate                references/templates/vision.md              reference      44    1556      389        335
devlyn:ideate                SUBTOTAL                                                  726   44407    11099       7912

devlyn:queue                 SKILL.md                                    cold_start     26    2520      630        503
devlyn:queue                 SUBTOTAL                                                   26    2520      630        503

devlyn:resolve               SKILL.md                                    cold_start    326   39369     9842       6293
devlyn:resolve               references/free-form-mode.md                reference      83    7489     1872       1327
devlyn:resolve               references/phases/build-gate.md             reference      45    3987      996        686
devlyn:resolve               references/phases/cleanup.md                reference      39    2597      649        476
devlyn:resolve               references/phases/implement.md              reference      42    3123      780        573
devlyn:resolve               references/phases/plan.md                   reference      43    3804      951        706
devlyn:resolve               references/phases/probe-derive.md           reference     255   15332     3833       2568
devlyn:resolve               references/phases/verify.md                 reference     278   18364     4591       3093
devlyn:resolve               references/state-schema.md                  reference     119   10963     2740       1689
devlyn:resolve               SUBTOTAL                                                 1230  105028    26254      17411

root-cause-analysis          SKILL.md                                    cold_start     65    2984      746        610
root-cause-analysis          SUBTOTAL                                                   65    2984      746        610

ui-implementation-standards  SKILL.md                                    cold_start     74    3962      990        742
ui-implementation-standards  SUBTOTAL                                                   74    3962      990        742

asset-creator                SKILL.md                                    cold_start    291   10488     2622       1833
asset-creator                SUBTOTAL                                                  291   10488     2622       1833

better-auth-setup            SKILL.md                                    cold_start    661   26634     6658       4599
better-auth-setup            references/api-keys.md                      reference     236    7646     1911       1188
better-auth-setup            references/config-and-entry.md              reference     239    7466     1866       1187
better-auth-setup            references/middleware.md                    reference     409   12562     3140       2050
better-auth-setup            references/proxy-gotchas.md                 reference     148    8316     2079       1433
better-auth-setup            references/proxy-setup.md                   reference     284   10439     2609       1528
better-auth-setup            references/schema.md                        reference     224    9463     2365       1184
better-auth-setup            references/testing.md                       reference     241    7346     1836       1101
better-auth-setup            SUBTOTAL                                                 2442   89872    22464      14270

cloudflare-nextjs-setup      SKILL.md                                    cold_start    286   11162     2790       1929
cloudflare-nextjs-setup      SUBTOTAL                                                  286   11162     2790       1929

devlyn:pencil-pull           SKILL.md                                    cold_start    128    6824     1706       1258
devlyn:pencil-pull           SUBTOTAL                                                  128    6824     1706       1258

devlyn:pencil-push           SKILL.md                                    cold_start     75    4273     1068        829
devlyn:pencil-push           SUBTOTAL                                                   75    4273     1068        829

devlyn:reap                  SKILL.md                                    cold_start    105    5492     1373       1072
devlyn:reap                  SUBTOTAL                                                  105    5492     1373       1072

dokkit                       SKILL.md                                    cold_start    211   10109     2527       1928
dokkit                       references/docx-field-patterns.md           reference     151    4240     1060        650
dokkit                       references/docx-section-range-detection.md  reference     147    6190     1547       1136
dokkit                       references/docx-structure.md                reference      58    1798      449        254
dokkit                       references/field-detection-patterns.md      reference     130    4497     1124        838
dokkit                       references/hwpx-field-patterns.md           reference     461   15327     3831       2310
dokkit                       references/hwpx-structure.md                reference     159    6338     1584        863
dokkit                       references/image-opportunity-heuristics.md  reference     121    5543     1385        993
dokkit                       references/image-xml-patterns.md            reference     338   14334     3583       1890
dokkit                       references/section-image-interleaving.md    reference     346   13232     3308       1940
dokkit                       references/section-range-detection.md       reference     118    5058     1264        893
dokkit                       references/state-schema.md                  reference     143    4719     1179        914
dokkit                       references/supported-formats.md             reference      67    1669      417        332
dokkit                       SUBTOTAL                                                 2450   93054    23258      14941

generate-skill               SKILL.md                                    cold_start    178    6473     1618       1193
generate-skill               SUBTOTAL                                                  178    6473     1618       1193

polar-billing-setup          SKILL.md                                    cold_start     76    7700     1925       1469
polar-billing-setup          references/gotchas.md                       reference     111    6995     1748       1351
polar-billing-setup          references/setup.md                         reference     101    4431     1107        846
polar-billing-setup          SUBTOTAL                                                  288   19126     4780       3666

prompt-engineering           SKILL.md                                    cold_start    243    8044     2011       1457
prompt-engineering           SUBTOTAL                                                  243    8044     2011       1457

pyx-scan                     SKILL.md                                    cold_start    185    5687     1421       1063
pyx-scan                     SUBTOTAL                                                  185    5687     1421       1063

_shared                      adapters/README.md                          shared         67    3505      876        666
_shared                      adapters/claude.md                          shared         37    3139      784        586
_shared                      adapters/codex.md                           shared         33    3114      778        590
_shared                      adapters/omp.md                             shared         17     920      230        176
_shared                      codex-config.md                             shared         71    5844     1461       1009
_shared                      engine-preflight.md                         shared         55    5330     1332        962
_shared                      pair-plan-schema.md                         shared        298   18748     4687       2678
_shared                      runtime-principles.md                       shared        101   14508     3627       2852
_shared                      SUBTOTAL                                                  679   55108    13775       9519

(root)                       CLAUDE.md                                   root          176   24016     6004       4546
(root)                       AGENTS.md                                   root          110    9678     2419       1804
(root)                       SUBTOTAL                                                  286   33694     8423       6350

GRAND TOTAL                                                                          10578  549833   137435      94091
```

## Top-3 heaviest artifacts

`devlyn:resolve` is the single heaviest skill (26,254 tok≈c/4 across SKILL.md +
8 reference files) — expected, since it is the one REQUIRED pipeline skill and
carries the full PLAN→VERIFY reference set. `dokkit` (23,258) and
`better-auth-setup` (22,464) are the next heaviest, both `optional-skills/`
entries only loaded when the user explicitly installs them, not part of the
default cold-start surface. `_shared/pair-plan-schema.md` (4,687) and
`_shared/runtime-principles.md` (3,627) are the heaviest individual `_shared`
docs, and `CLAUDE.md` alone (6,004) outweighs any single `devlyn:*` SKILL.md
except `devlyn:resolve`'s.
