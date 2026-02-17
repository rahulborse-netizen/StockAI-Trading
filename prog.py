import functools

def partial1(func, *args, **kwargs):
    # Write your code here
    return functools.partial(func, *args, **kwargs)

def add(a, b):
    # Write your code here
    return a+b

def concat(a, b):
    # Write your code here
    return str(a) + str(b)

def power(a, b):
    # Write your code here
    return a**b

def parse_token(t):
    # Write your code here
    if '=' in t:
        key, value = t.split('=', 1)
        try:
            value = int(value)
        except ValueError:
            pass
        return (key, value)
    else:
        try:
            return int(t)
        except ValueError:
            return t

def solve():
    fname = input().strip()
    pre_line = input().strip()
    new_line = input().strip()
    
    func_map = {"add": add, "concat": concat, "power": power}
    func = func_map.get(fname, concat)
    
    pre_args, pre_kwargs = [], {}
    new_args, new_kwargs = [], {}
    
    # parse pre-filled args
    if pre_line:
        for tok in pre_line.split():
            parsed = parse_token(tok)
            if isinstance(parsed, tuple):
                pre_kwargs[parsed[0]] = parsed[1]
            else:
                pre_args.append(parsed)
    
    # parse new args
    if new_line:
        for tok in new_line.split():
            parsed = parse_token(tok)
            if isinstance(parsed, tuple):
                new_kwargs[parsed[0]] = parsed[1]
            else:
                new_args.append(parsed)
    
    f = partial1(func, *pre_args, **pre_kwargs)
    print(f(*new_args, **new_kwargs))

if __name__ == "__main__":
    solve()
