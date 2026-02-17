"""
Frequency counting: Count occurrences of each element in a list.
"""

def count_freq(nums):
    freq = {}
    for num in nums:
        freq[num] = freq.get(num, 0) + 1
    return freq


# Verification
if __name__ == "__main__":
    nums = [1, 2, 2, 3, 1, 2, 4, 1]
    result = count_freq(nums)
    expected = {1: 3, 2: 3, 3: 1, 4: 1}
    assert result == expected, f"Expected {expected}, got {result}"
    print("freq =", result)
    print("Check passed: frequency counting works correctly.")
