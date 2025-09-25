from typing import List, Tuple
#rom local_driver import Alg3D, Board   # ローカル検証用
from framework import Alg3D, Board

class MyAI(Alg3D):
    def get_move(
        self,
        board: List[List[List[int]]],
        player: int,
        last_move: Tuple[int, int, int]
    ) -> Tuple[int, int]:
        # ここにアルゴリズムを書く