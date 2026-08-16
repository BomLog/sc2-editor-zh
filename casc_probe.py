import casc, _casc, inspect
print("=== _casc members ===")
print([n for n in dir(_casc) if not n.startswith('__')])
print("=== _casc doc ===")
print(getattr(_casc, '__doc__', None))
for fn in ['open', 'close', 'find_first_file', 'find_next_file', 'find_close', 'open_file', 'read_file', 'close_file']:
    f = getattr(_casc, fn, None)
    if f:
        try:
            print(fn, '->', f.__doc__)
        except Exception as e:
            print(fn, 'no doc', e)
# locate the pyd
print("=== _casc file ===")
print(_casc.__file__)
