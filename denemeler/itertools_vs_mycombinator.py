import string
import time

def generate_combinations(charset: str, length: int = 4):
    current = [0] * length
    max_index = len(charset) - 1
    while True:
        result = ''.join(charset[i] for i in current)
        yield result

        pos= length -1
        while pos >= 0:
            if current[pos] < max_index:
                current[pos] += 1
                break
            else:
                current[pos] = 0
                pos -= 1
        if pos < 0:
            break

def generate_itertools(charset: str, length: int = 4):
    from itertools import product
    for password in product(charset, repeat=length):
        yield "".join(password)

if __name__ == "__main__":
    charset = string.digits
    for i_ in range(1,16):
        start_time1 = time.time()
        generator1 = generate_combinations(charset, i_)

        for _ in range(len(charset) ** i_):
            next(generator1)

        print(f"Itertools Time {i_}: {time.time() - start_time1}")
        
        start_time2 = time.time()
        generator2= generate_itertools(charset, i_)

        for _ in range(len(charset) ** i_):
            next(generator2)
        
        print(f"My Generator Time {i_}: {time.time() - start_time2}")


# Itertools Time 1: 0.0
# My Generator Time 1: 0.0
# Itertools Time 2: 0.0
# My Generator Time 2: 0.0
# Itertools Time 3: 0.001001596450805664
# My Generator Time 3: 0.0
# Itertools Time 4: 0.01200413703918457
# My Generator Time 4: 0.004179954528808594
# Itertools Time 5: 0.1315925121307373
# My Generator Time 5: 0.03213214874267578
# Itertools Time 6: 1.6215403079986572
# My Generator Time 6: 0.32564806938171387
# Itertools Time 7: 14.76832890510559
# My Generator Time 7: 3.636117458343506
# Itertools Time 8: 170.18690490722656
# My Generator Time 8: 40.19899392127991