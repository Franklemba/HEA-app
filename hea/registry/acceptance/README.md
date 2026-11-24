# Registry acceptance checks

One script per phase. Each runs the phase's end-to-end test with test users, inside one transaction, and rolls
everything back (scans written to disk are removed too). Run from the bench's `sites` folder:

    cd ~/frappe-bench-dev/sites && ../env/bin/python ../apps/hea/hea/registry/acceptance/phase3.py

Phase 1 also needs the text of the 2020 file index at /tmp/hea_index.txt.

The checks add their own test users and Departmental Heads; remove the Test Lab first (Registry Lab → Remove Lab Completely) so the lab heads are not picked up instead.
