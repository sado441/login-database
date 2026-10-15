# Third-party references

SEGE Open Source, s3rc4nn1/SEGE-MACRO:
https://github.com/s3rc4nn1/SEGE-MACRO

The local compatibility behavior in sege_compat.py and local_windows.py is
adapted from the supplied project's macros/multi.py, multi - canli.py and
background.py. The upstream MIT license and notice are included verbatim
in SEGE_LICENSE.txt. Changes in this implementation include explicit window
selection, extended-key handling, error reporting and coordinated cleanup.

The separately downloaded Interception library and installer have their own
upstream license terms: https://github.com/oblitum/Interception. These binaries
are not included in SADO-Link.zip; prepare_interception.py downloads the
official archive and preserves its LGPL license alongside the prepared files.
