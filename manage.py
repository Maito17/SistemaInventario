#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

# Workaround for Django 6.0 + mysqlclient compatibility issue
# Django 6.0 expects Database.__version__ but mysqlclient 2.2+ doesn't have it
try:
    import MySQLdb
    if not hasattr(MySQLdb, '__version__'):
        # Create __version__ from version_info tuple
        MySQLdb.__version__ = '.'.join(map(str, MySQLdb.version_info[:3]))
except ImportError:
    pass  # MySQLdb not installed, Django will handle this


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'possitema.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
