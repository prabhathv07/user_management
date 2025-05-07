from typing import List
from itertools import combinations

class Solution:
    def countGoodTriplets(self, arr: List[int], a: int, b: int, c: int) -> int:
        return sum(
            abs(arr[i]-arr[k]) <= c 
            for i,j,k in combinations(range(len(arr)), 3)
            if abs(arr[i]-arr[j]) <= a and abs(arr[j]-arr[k]) <= b
        )
