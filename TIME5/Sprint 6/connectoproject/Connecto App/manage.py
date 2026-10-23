#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

def main():
    """Executa os comandos administrativos do Django."""

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'connectoproject.settings')

    try:
        from django.core.management import execute_from_command_line

    except ImportError as exc:
        raise ImportError(
            "Não foi possível importar o Django. "
            "Verifique se ele está instalado."
        ) from exc

    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
