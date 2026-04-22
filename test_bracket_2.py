def generate_bracket(n: int) -> list[int]:
    import math
    if n <= 1:
        return [1]
    matches = [1, 2]
    for _ in range(1, int(math.log2(n))):
        next_matches = []
        length = len(matches) * 2
        for seed in matches:
            next_matches.append(seed)
            next_matches.append(length + 1 - seed)
        matches = next_matches
    return matches

qualifiers = [1, 2, 3, 4, 5]
import math
full_size = 2 ** math.ceil(math.log2(len(qualifiers)))
byes = full_size - len(qualifiers)
seeds = qualifiers[:] + [None] * byes

bracket_positions = generate_bracket(full_size)
pairings = []
for i in range(0, full_size, 2):
    top_seed_idx = bracket_positions[i] - 1
    bot_seed_idx = bracket_positions[i+1] - 1
    pairings.append((seeds[top_seed_idx], seeds[bot_seed_idx]))

print("Pairings:", pairings)
