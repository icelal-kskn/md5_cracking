from numba import jit

@jit(nopython=True, nogil=True)
def next_combination(current, max_index, length):
    pos = length - 1
    while pos >= 0:
        if current[pos] < max_index:
            current[pos] += 1
            return True
        else:
            current[pos] = 0
            pos -= 1
    return False

def generate_combinations_w_jit(charset, length=4):
    current = [0] * length
    max_index = len(charset) - 1
    
    while True:
        yield ''.join(charset[i] for i in current)
        if not next_combination(current, max_index, length):
            break


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
    

if __name__ == "__main__":
    import string
    import time

    charset = string.digits
    for i in range(1, 16):
        
        # İlk test: JIT'li versiyon
        start_time1 = time.time()
        generator1 = generate_combinations_w_jit(charset, i)
        count = len(charset) ** i
        for _ in range(count):
            next(generator1)
        print(f"JIT Time {i}: {time.time() - start_time1}")

        # İkinci test: Normal versiyon
        start_time2 = time.time()
        generator2 = generate_combinations(charset, i)
        for _ in range(count):  # Aynı sayıda iterasyon yapmalı
            next(generator2)
        print(f"Normal Time {i}: {time.time() - start_time2}")
        print("-" * 30)
        

# JIT Time 1: 0.9499912261962891
# Normal Time 1: 0.0
# ------------------------------
# JIT Time 2: 0.000997304916381836
# Normal Time 2: 0.001003265380859375
# ------------------------------
# JIT Time 3: 0.012198209762573242
# Normal Time 3: 0.001003265380859375
# ------------------------------
# JIT Time 4: 0.11461758613586426
# Normal Time 4: 0.01500082015991211
# ------------------------------
# JIT Time 5: 1.2976741790771484
# Normal Time 5: 0.13688302040100098
# ------------------------------
# JIT Time 6: 14.082961797714233
# Normal Time 6: 1.4074161052703857
# ------------------------------