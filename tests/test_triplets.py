from typing import List
from app.utils.triplet_counter import Solution
import pytest

class TestTripletSolution:
    def test_basic_case(self):
        sol = Solution()
        arr = [3,0,1,1,9,7]
        assert sol.countGoodTriplets(arr, 7, 2, 3) == 4

    def test_empty_array(self):
        sol = Solution()
        assert sol.countGoodTriplets([], 0, 0, 0) == 0

    def test_insufficient_elements(self):
        sol = Solution()
        assert sol.countGoodTriplets([1,2], 1, 1, 1) == 0

    @pytest.mark.parametrize('arr,a,b,c,expected', [
        ([3,0,1,1,9,7], 7, 2, 3, 4),
        ([1,1,2,2,3], 0, 0, 0, 0),
        ([4,5,6], 1, 1, 1, 0),
        ([7,8,9,10], 3, 3, 3, 4)
    ])
    def test_various_cases(self, arr, a, b, c, expected):
        assert Solution().countGoodTriplets(arr, a, b, c) == expected

    def test_performance(self):
        large_arr = list(range(100))
        result = Solution().countGoodTriplets(large_arr, 10, 10, 10)
        assert result > 0  # Actual value would need calculation
