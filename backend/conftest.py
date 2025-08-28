"""Root pytest configuration (kept intentionally minimal).

The application package resides in the nested `app/` directory. Because the
pytest rootdir is the backend directory, Python can already discover the
`app` package without path manipulation as long as we avoid having an
`__init__` at the backend root (which would shadow the real package).
"""

# Intentionally no path mangling here.
