"""
debug_discovery.py

Run this once locally (with a valid cookies.json already saved) to verify
fetch_enrolled_courses() and fetch_course_assignments() actually find your
real courses and assignments, before trusting them in the scheduled poller.

Usage: python debug_discovery.py
"""

import scraper

client = scraper.get_client()

if not scraper.verify_session(client):
    print("Session invalid — run auto_login.py or relogin.py first.")
    raise SystemExit(1)

print("Discovering enrolled courses...")
courses = scraper.fetch_enrolled_courses(client)
print(f"Found {len(courses)} course(s):")
for c in courses:
    print(f"  - [{c['id']}] {c['title']} -> {c['url']}")

if not courses:
    print("\nNo courses found — the dashboard page's HTML structure probably")
    print("doesn't match the /course/view.php?id=N pattern the code looks for.")
    print("Paste the raw HTML of https://lms.vit.ac.in/my/ here so the")
    print("selector can be corrected against the real structure.")
    raise SystemExit(1)

print("\nDiscovering assignments per course...")
for c in courses:
    assignments = scraper.fetch_course_assignments(client, c["id"])
    print(f"\n{c['title']} ({len(assignments)} assignment(s)):")
    for a in assignments:
        print(f"  - [{a['id']}] {a['title']} -> {a['url']}")
    if not assignments:
        print("  (none found — if you know this course has assignments,")
        print(f"   paste the raw HTML of {scraper.BASE_URL}/mod/assign/index.php?id={c['id']}")
        print("   here so the table-parsing logic can be corrected.)")