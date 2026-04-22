def generate_bracket(n: int):
    import math
    rounds = int(math.log2(n))
    matches = [1, 2]
    for _ in range(1, rounds):
        next_matches = []
        length = len(matches) * 2
        for seed in matches:
            next_matches.append(seed)
            next_matches.append(length + 1 - seed)
        matches = next_matches
    return matches

print("4 teams:", generate_bracket(4))
print("8 teams:", generate_bracket(8))
print("16 teams:", generate_bracket(16))
