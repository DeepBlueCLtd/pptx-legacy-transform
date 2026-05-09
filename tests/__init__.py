"""Test package for the PPTX-to-DITA migration pipeline.

Discover and run with the standard library only (FR-017, R13):

    python -m unittest discover tests/

Conventions:

* Ephemeral fixtures (mock PPTX, intermediate CSVs, generated DITA
  trees) are written under ``tests/_tmp/`` and never committed.
* No fixture larger than 50 KB is committed (R13).
* The mock PPTX is generated on demand via
  ``tests.conftest_helpers.make_mock_pptx`` rather than committed.

Expected runtime: under one minute on a standard development workstation
(SC-003). On the air-gapped network: when a test fails, read the
log file produced by the script under test (``extract.log``,
``generate.log``, ``introspect.log``) for context. Tests are designed
to fail loud rather than silent; if a failure message does not name a
file under ``tests/`` you have probably hit an environment-level issue
(missing ``python-pptx``, wrong Python version) rather than a code
regression.
"""
