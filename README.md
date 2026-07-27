# blast
Build an impact-check skill that scans all repos under ~/work/ to trace cross-repo callers of changed modules, maps test coverage on changed paths, and appends a structured IMPACT CHECK REPORT to the PR description automatically. Issues a non-blocking CAUTION warning with a suggested next skill when high-impact callers or coverage gaps are detected
