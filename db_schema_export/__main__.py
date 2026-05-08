"""Entry point for running as: python -m db_schema_export"""

import sys

from db_schema_export.cli import main

if __name__ == "__main__":
    sys.exit(main())
