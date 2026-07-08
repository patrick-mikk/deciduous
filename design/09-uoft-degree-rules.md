# 09 — UofT Arts & Science Degree Rules (domain model)

The real rules behind the progress dashboard, the plan validator, and the
requirement views. Sourced from the UofT Academic Calendar (see bottom). Rules
current as of the 2025-26 calendar; **store an effective-year** with each rule
because they change (e.g. the one-type-per-subject rule took effect Sept 2025).

## 1. The degree (HBA / HBSc / BCom)
- **20.0 credits total**; **≥10.0 must be Arts & Science** credits.
- **Program requirement — complete ONE of:**
  - 1 **Specialist**, OR
  - 2 **Majors**, OR
  - 1 **Major + 2 Minors**.
- **Distinct-credits rule:** any multi-program combination needs **≥12.0
  *different* credits** across the programs (a course double-counted between two
  programs counts once toward this 12.0).
- **Level distribution:** **≥13.0 credits at the 200+ level**, and **≥6.0 credits
  at the 300+ level**. **≤1.0 transfer credit** may count toward the 300+ minimum
  (except U of T exchange).
- **Same-subject cap:** **≤15.0 credits** may share the same three-letter
  designator (e.g. no more than 15.0 `POL`).
- **Minimum 1.85 CGPA** to graduate; must be in good standing.
- **HBA vs HBSc** is determined by the *area* of the programs (Arts vs Science).
  Some cross-area combinations (e.g. a Science Major + an Arts Major) let the
  student **choose** HBA or HBSc.
- **Passing grade** = 50% / `P` / `CR`.

## 2. Program types (POSt)
| Type | Code | Credits | Upper-level minimums |
|------|------|---------|----------------------|
| **Specialist** | `ASSPE` | 10.0–14.0 (interdisc. up to 16.0) | ≥4.0 at 300+, of which ≥1.0 at 400 |
| **Major** | `ASMAJ` | 6.0–8.0 | ≥2.0 at 300+, of which ≥0.5 at 400 |
| **Minor** | `ASMIN` | 4.0 | ≥1.0 at 300+ |
| **Focus** | `ASFOC` | thematic cluster inside a Specialist/Major; appears on transcript | — |
| **Certificate** | `ASCER` | 2.0–3.0; **does not** count toward degree *program* requirements | — |

- **One-type-per-subject (eff. Sept 2025):** only **one** of Specialist / Major /
  Minor per subject area (same final 4-digit code). E.g. not both a Major and Minor
  in Sociology.
- **Streams:** specialised emphases within a Specialist/Major, differing in upper
  years (the `A/B/C` suffix we already see, e.g. `ASMAJ1305A`).
- **Program code:** `AS` + 3-letter type + 4-digit subject (`ASSPE0608`).

## 3. Program enrolment (matters for planning & alerts)
- Enrol in programs **after completing 4.0 credits** (or on track to by September).
- **Open programs:** no restriction beyond the 4.0 credits.
- **Limited programs:** require some of — completed prerequisite courses with
  minimum grades, a **Variable Minimum Grade / grade average** (set yearly by
  demand), or an **application / audition / supplementary** submission.
- The Calendar's **enrolment-requirements** field carries this text per program
  (already in our `Program.enrolmentRequirements`).

## 4. Breadth Requirement (the 5 categories)
| BR | Category |
|----|----------|
| 1 | Creative and Cultural Representations |
| 2 | Thought, Belief, and Behaviour |
| 3 | Society and Its Institutions |
| 4 | Living Things and Their Environment |
| 5 | The Physical and Mathematical Universes |

- **Satisfied by EITHER:**
  - **1.0 credit in each of 4** of the 5 categories, **OR**
  - **1.0 credit in each of any 3** categories **+ 0.5 credit in each of the other 2**.
- **How courses count:** an **H (0.5-credit)** course = 0.5 toward **one** category.
  A **Y (1.0-credit)** course = either **0.5 in two** categories **or 1.0 in one**
  (as the course specifies, e.g. "BR=5" vs a split). Some courses have **no** breadth.
- **CR/NCR courses can still count toward breadth** even though they don't count
  toward program requirements or GPA.

## 5. Distribution (course classification)
Every course is classified **Arts** or **Science** (`distributionRequirements` in
TTB). This is not a separate hard requirement anymore but it drives: the **≥10.0
ArtSci** rule and the **HBA/HBSc** determination. Surface it, don't gate on it.

## 6. Grades, GPA, standing
### Grade scale (grade points)
| % | Letter | GP | · | % | Letter | GP |
|---|--------|----|---|---|--------|----|
| 90–100 | A+ | 4.0 | | 67–69 | C+ | 2.3 |
| 85–89 | A | 4.0 | | 63–66 | C | 2.0 |
| 80–84 | A- | 3.7 | | 60–62 | C- | 1.7 |
| 77–79 | B+ | 3.3 | | 57–59 | D+ | 1.3 |
| 73–76 | B | 3.0 | | 53–56 | D | 1.0 |
| 70–72 | B- | 2.7 | | 50–52 | D- | 0.7 |
| | | | | 0–49 | F | 0.0 |

- **CGPA** = weighted avg of all courses; **SGPA** = one session (Fall / Winter /
  whole Summer); **AGPA** = Fall+Winter of a year. Weight = course credit value.
- **Academic standing:** Good ≥ **1.50** CGPA · **Probation** (CGPA < 1.50 but
  sessional/annual ≥ 1.70) · **Suspension** (both < threshold) · Refused. On
  probation: **≤2.5 credits/term** (Fall, Winter), **≤1.0/Summer**.

### Grade notations — **excluded from GPA** unless noted
`AEG` (aegrotat) · `CR/NCR` · `Extra (EXT/XTR)` · `GWR` · `IPR` (in progress) ·
`LWD` (late withdrawal after drop) · `WDR` (late w/o penalty) · `SDF` (standing
deferred) · `P` (pass; `FL`/failure = 0.0 if calculated).
- **CR/NCR:** limited number of credits may be designated CR/NCR (verify the
  current cap, historically up to 2.0); excluded from GPA and from program
  requirements, **can** count toward the 20.0 and toward breadth.
- **Repeated courses / Extra:** a repeat can mark the earlier attempt **Extra**
  (Second Attempt for Credit policy); Extra courses don't count toward the degree
  or GPA. (We already see `(Extra)` flags in the Degree Explorer import.)

## 7. What the app must compute (validator surface)
For a student's transcript + planned courses + enrolled programs, evaluate:
1. **Degree progress:** total credits x/20.0; ArtSci credits x/10.0; 200+ x/13.0;
   300+ x/6.0 (cap transfer at 1.0); same-designator ≤15.0 warning.
2. **Program combination:** valid combo type; ≥12.0 distinct credits; one-type-per-
   subject; per-program credits x/y and 300+/400 minimums.
3. **Breadth:** per-category earned credits + which of the two satisfaction options
   is closest; "you need 0.5 more in BR2" guidance.
4. **GPA:** SGPA/AGPA/CGPA from marks (respecting notations & Extra); good-standing
   check; probation course-load cap.
5. **Prereqs / coreqs / exclusions:** per planned course, against completed+planned.
6. **Enrolment eligibility:** for a target Limited program, does the student meet the
   prereq-grade / average criteria (from `enrolmentRequirements`)?
7. **Graduation eligibility:** all of the above green + CGPA ≥ 1.85.

## Sources
- [HBA/HBSc Requirements — Academic Calendar](https://artsci.calendar.utoronto.ca/hbahbsc-requirements)
- [Understanding Programs & Certificates](https://artsci.calendar.utoronto.ca/understanding-programs-and-certificates)
- [Academic Record (grade scale & notations)](https://artsci.calendar.utoronto.ca/academic-record)
- [What is a breadth requirement? — Sidney Smith Commons](https://sidneysmithcommons.artsci.utoronto.ca/what-is-a-breadth-requirement/)
