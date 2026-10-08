### A.1 Check the files against a seal list

In the folder that holds a seal list, run `sha256sum -c --ignore-missing <list>`. A listed file that is not published is skipped by `--ignore-missing`; the public record's `WITHHELD.json` records the hash each skipped file had. For the whole public record, run `python check_public.py` in its top folder; it ends with `DONE CHECK: ALL PASS`.

### A.2 Check a FreeTSA time stamp

Download `cacert.pem` and `tsa.crt` from freetsa.org, then run `openssl ts -verify -in <file>.tsr -data <file> -CAfile cacert.pem -untrusted tsa.crt`. It should print `Verification: OK`. The stamped file is the seal list, not the files it lists.

### A.3 Check an OpenTimestamps (Bitcoin) proof

Run `ots verify <file>.ots` with the OpenTimestamps client, next to the stamped file. A proof made recently may show only a calendar attestation; run `ots upgrade <file>.ots` once online to pick up the Bitcoin block when one exists.

### A.4 Check a number in this report

Every count in a card names a file and a quoted line (Appendix B). Open the file, find the line, compare. The same check runs in bulk with `python build.py --verify-sources` on a machine that holds the source files.

### A.5 Rebuild this report

Run `python build.py --pdf` in the report's folder (Python 3, standard library only). It checks the data, renders `dist/report.md`, `dist/report.html` and `dist/paper.md`, and prints `dist/report.pdf` if a PDF tool is configured. It fails if a number in the prose is not in a finding file.
