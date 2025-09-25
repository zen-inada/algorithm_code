
#※変更禁止※
#ターミナルでpython local_driver.pyと打つと次の手をかえしてくれる。
# === local_driver.py ===
import importlib.util
from typing import List, Tuple
from abc import ABC, abstractmethod
from stub_board import board

Board = List[List[List[int]]] 

class Alg3D(ABC):
    @abstractmethod
    def get_move(
        self, board: Board, player: int, last_move: Tuple[int, int, int]
    ) -> Tuple[int, int]:
        """次の一手 (x,y) を返す"""
        ...

def create_board() -> Board:
    return [[[0 for _ in range(4)] for _ in range(4)] for _ in range(4)]

def place_disk(board: Board, x: int, y: int, player: int) -> bool:
    for z in range(4):
        if board[z][y][x] == 0:
            board[z][y][x] = player
            return True
    return False  

def load_ai(path: str = "main.py"):
    spec = importlib.util.spec_from_file_location("student_ai", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  

    if not hasattr(module, "MyAI"):
        raise AttributeError("main.py に MyAI クラスが定義されていません")

    ai = module.MyAI()
    if not hasattr(ai, "get_move"):
        raise TypeError("MyAI は get_move を実装している必要があります")

    return ai

if __name__ == "__main__":
    ai = load_ai()

    def is_column_full(board, x, y) -> bool:
        for z in range(4):
            if board[z][y][x] == 0:
                return False
        return True

    player = 1
    last_move = (2, 3, 0)

    x, y = ai.get_move(board, player, last_move)

    print("AI の出力:", (x, y))
