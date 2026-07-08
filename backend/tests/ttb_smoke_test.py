#!/usr/bin/env python3
"""
Smoke test for the UofT Timetable Builder (TTB) API.

Verifies the endpoints the degree planner's data layer depends on:
  - GET  /reference-data              -> valid sessions / divisions / campuses
  - POST /getPageableCourses          -> paged course search with full sections
  - GET  /getCoursesByCodeAndSectionCode/<CODE> -> single-course lookup

Run:  python backend/tests/ttb_smoke_test.py
No third-party deps (uses urllib) so it runs anywhere, including cPanel shell.
"""

import json
import sys
import time
import urllib.request
import urllib.error

BASE = "https://api.easi.utoronto.ca/ttb"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Origin": "https://ttb.utoronto.ca",
    "User-Agent": "Mozilla/5.0 (degree-planner smoke test)",
}

# Day integer -> weekday, confirmed empirically (1=Mon .. 7=Sun, ISO-8601).
DAYS = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}


def _get(path):
    req = urllib.request.Request(BASE + path, headers=HEADERS)
    try:
        r = urllib.request.urlopen(req, timeout=40)
        return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def _post(path, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(BASE + path, data=data, headers=HEADERS, method="POST")
    try:
        r = urllib.request.urlopen(req, timeout=40)
        return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def build_search_payload(course_code="", sessions=("20265",), divisions=("ARTSC",),
                         page=1, page_size=20):
    """The getPageableCourses request body, matching the TTB Angular client."""
    return {
        "courseCodeAndTitleProps": {
            "courseCode": course_code,
            "courseTitle": "",
            "courseSectionCode": "",
            "searchCourseDescription": False,
        },
        "departmentProps": [],
        "campuses": [],
        "sessions": list(sessions),
        "requirementProps": [],
        "instructorProps": [],
        "courseLevels": [],
        "deliveryModes": [],
        "dayPreferences": [],
        "timePreferences": [],
        "divisions": list(divisions),
        "creditWeights": [],
        "availableSpace": False,
        "waitListable": False,
        "page": page,
        "pageSize": page_size,
        "direction": "asc",
    }


def hhmm(millis_of_day):
    minutes = millis_of_day // 60000
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def get_current_sessions():
    """Return list of selectable full-session codes (header=False, numeric)."""
    status, body = _get("/reference-data")
    assert status == 200, f"reference-data returned {status}"
    payload = json.loads(body)["payload"]
    sessions = payload["currentSessions"]
    full = [s["value"] for s in sessions if not s.get("header") and s["value"].isdigit()]
    return sessions, full


def main():
    failures = []

    print("== 1. reference-data ==")
    sessions, full_sessions = get_current_sessions()
    print(f"   current sessions: {[s['value'] for s in sessions if not s.get('header')]}")
    print(f"   usable full-session codes: {full_sessions}")
    if not full_sessions:
        failures.append("no usable session codes")
    session = full_sessions[0] if full_sessions else "20265"

    print(f"\n== 2. getPageableCourses (session {session}, ARTSC) ==")
    t0 = time.time()
    status, body = _post("/getPageableCourses",
                         build_search_payload(sessions=(session,), page=1, page_size=20))
    if status != 200:
        failures.append(f"getPageableCourses status {status}: {body[:120]!r}")
        print(f"   FAIL status={status}")
    else:
        pc = json.loads(body)["payload"]["pageableCourse"]
        print(f"   total={pc['total']} returned={len(pc['courses'])} in {time.time()-t0:.2f}s")
        # verify pagination is disjoint
        p1 = {c["code"] for c in pc["courses"]}
        _, body2 = _post("/getPageableCourses",
                         build_search_payload(sessions=(session,), page=2, page_size=20))
        p2 = {c["code"] for c in json.loads(body2)["payload"]["pageableCourse"]["courses"]}
        print(f"   page1/page2 disjoint: {p1.isdisjoint(p2)}")
        if not p1.isdisjoint(p2):
            failures.append("pagination pages overlap")

        # verify catalog + schedule fields exist on a course
        sample = max(pc["courses"],
                     key=lambda c: sum(len(s.get("meetingTimes", [])) for s in c.get("sections", [])))
        cm = sample.get("cmCourseInfo") or {}
        print(f"\n   sample course: {sample['code']} - {sample['name']}")
        for field in ("description", "prerequisitesText", "exclusionsText",
                      "corequisitesText", "breadthRequirements"):
            present = "OK " if field in cm else "MISSING"
            if field not in cm:
                failures.append(f"cmCourseInfo missing {field}")
            print(f"     cmCourseInfo.{field:20} {present}")
        print(f"   sections: {len(sample.get('sections', []))} "
              f"methods={sorted({s.get('teachMethod') for s in sample.get('sections', [])})}")
        for sec in sample.get("sections", [])[:4]:
            for mt in sec.get("meetingTimes", []):
                st, en = mt["start"], mt["end"]
                print(f"     {sec['name']:8} {DAYS.get(st['day'], '?')} "
                      f"{hhmm(st['millisofday'])}-{hhmm(en['millisofday'])} "
                      f"[{sec.get('currentEnrolment')}/{sec.get('maxEnrolment')}]")

    print("\n== 3. getCoursesByCodeAndSectionCode ==")
    status, body = _get("/getCoursesByCodeAndSectionCode/APM462H1")
    ok = status == 200 and b'"pageableCourse"' in body
    print(f"   status={status} usable={ok} bytes={len(body)}")
    if not ok:
        failures.append(f"getCoursesByCodeAndSectionCode status {status}")

    print("\n" + ("PASS - all TTB endpoints healthy" if not failures
                  else "FAIL:\n  - " + "\n  - ".join(failures)))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
