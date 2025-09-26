from typing import List, Tuple
#from local_driver import Alg3D, Board # ローカル検証用
from framework import Alg3D, Board # 本番用

class MyAI:
    def get_move(self, board: Board) -> Tuple[int, int]:
        # ==== 時間管理 ====
        from time import perf_counter
        T_SOFT = 2.4  # 約3秒CPU制限の安全側
        t0 = perf_counter()

        # ==== 基本ユーティリティ ====
        def count_stones(b):
            c1=c2=0
            for z in range(4):
                for y in range(4):
                    for x in range(4):
                        v=b[z][y][x]
                        if v==1: c1+=1
                        elif v==2: c2+=1
            return c1,c2

        # 先手=1, 後手=2 をカウントで推定
        c1,c2 = count_stones(board)
        me = 1 if c1==c2 else 2
        opp = 3 - me

        # 合法手: 列(x,y)が満杯でない（zに0がある）
        def legal_moves(b):
            ms=[]
            for y in range(4):
                for x in range(4):
                    if b[3][y][x]==0:  # 最上段が埋まっていなければ置ける
                        ms.append((x,y))
            # 中央寄りにソート
            def center_score(m):
                x,y=m
                return (abs(x-1.5)+abs(y-1.5))
            ms.sort(key=center_score)
            return ms

        # その列で実際に置かれるz（最下段から）
        def drop_z(b,x,y):
            for z in range(4):
                if b[z][y][x]==0: return z
            return None

        # --- 勝敗ライン（サーバ実装と同等の生成） ---
        DIRS = [(1,0,0),(0,1,0),(0,0,1),
                (1,1,0),(1,-1,0),(1,0,1),(1,0,-1),
                (0,1,1),(0,1,-1),(1,1,1),(1,1,-1),(1,-1,1),(-1,1,1)]
        LINES=[]
        for x in range(4):
            for y in range(4):
                for z in range(4):
                    for dx,dy,dz in DIRS:
                        line=[]
                        for i in range(4):
                            nx,ny,nz=x+dx*i,y+dy*i,z+dz*i
                            if 0<=nx<4 and 0<=ny<4 and 0<=nz<4:
                                line.append((nx,ny,nz))
                            else:
                                break
                        if len(line)==4:
                            LINES.append(line)

        def is_win(b, player):
            for line in LINES:
                ok=True
                for (x,y,z) in line:
                    if b[z][y][x]!=player:
                        ok=False; break
                if ok: return True
            return False

        # 局面評価（軽量だが鋭い）
        # 自分だけのライン: 1,4,32,10000 / 相手だけは反対符号
        W = [0, 1, 4, 32, 10000]
        def eval_board(b):
            # 即勝ち/負け優先（大値）
            if is_win(b, me):  return  10**9
            if is_win(b, opp): return -10**9
            score=0
            # 列の現在高さ（重力の“実現性”に微加点）
            heights=[[0]*4 for _ in range(4)]
            for y in range(4):
                for x in range(4):
                    h=0
                    for z in range(4):
                        if b[z][y][x]!=0: h=z+1
                    heights[y][x]=h
            for line in LINES:
                cm=co=0
                feas=0
                for (x,y,z) in line:
                    v=b[z][y][x]
                    if v==me: cm+=1
                    elif v==opp: co+=1
                    else:
                        # そのマスが“次手～数手で到達可能”なら微加点
                        if heights[y][x]<=z: feas+=1
                if cm and co: continue
                if cm:
                    score += W[cm] + feas
                elif co:
                    score -= W[co] + feas
            return score

        # 盤→キー（TT用）
        def key_of(b, turn):
            flat=[]
            for z in range(4):
                for y in range(4):
                    for x in range(4):
                        flat.append(b[z][y][x])
            return tuple(flat)+(turn,)

        # 1手適用/元に戻す（インプレースで速い）
        def do_move(b,x,y,player):
            z=drop_z(b,x,y)
            b[z][y][x]=player
            return z
        def undo_move(b,x,y,z):
            b[z][y][x]=0

        # 即勝ち＆即ブロックの優先
        def pick_tactical(b):
            moves = legal_moves(b)
            for (x,y) in moves:
                z = drop_z(b,x,y); b[z][y][x]=me
                if is_win(b, me): 
                    b[z][y][x]=0; return (x,y)
                b[z][y][x]=0
            for (x,y) in moves:
                z = drop_z(b,x,y); b[z][y][x]=opp
                if is_win(b, opp): 
                    b[z][y][x]=0; return (x,y)
                b[z][y][x]=0
            return None

        tact = pick_tactical(board)
        if tact: return tact  # まずは即勝/即ブロック

        # Negamax + αβ + TT + 反復深化
        TT = {}  # key -> (depth, flag, value)  flag: 0=exact, -1=upper, +1=lower
        BEST=(None, -10**12)

        def time_up(): return (perf_counter()-t0) >= T_SOFT

        def negamax(b, depth, alpha, beta, turn):  # turn: 手番（me or opp）
            if time_up():
                # 時間切れ時は静的値を返す
                return eval_board(b)

            k = key_of(b, turn)
            ent = TT.get(k)
            if ent and ent[0] >= depth:
                flag, val = ent[1], ent[2]
                if flag==0:   return val
                if flag>0 and val>alpha: alpha = val
                elif flag<0 and val<beta: beta = val
                if alpha>=beta: return val

            # 終端 or 深さ尽き
            if depth==0:
                return eval_board(b)

            # 合法手
            moves = legal_moves(b)
            if not moves:
                return eval_board(b)

            # 手注文：中央優先 + 試し勝ち/ブロックを前へ
            # すでにタクティカルで即勝はない前提だが一応先に置く
            ordered=[]
            for (x,y) in moves:
                z=drop_z(b,x,y); b[z][y][x]=turn
                sc = 0
                if is_win(b,turn): sc += 10**7
                b[z][y][x]=0
                # 中央寄り
                sc -= (abs(x-1.5)+abs(y-1.5))*10
                ordered.append((sc,x,y))
            ordered.sort(reverse=True)

            val = -10**12
            nxt = 3 - turn
            a0 = alpha
            for _,x,y in ordered:
                z=do_move(b,x,y,turn)
                v = -negamax(b, depth-1, -beta, -alpha, nxt)
                undo_move(b,x,y,z)
                if v>val:
                    val=v
                    if turn==me and depth==cur_depth and v>BEST[1]:
                        # 反復深化の現在深さで最善着手更新
                        BEST=( (x,y), v )
                if val>alpha: alpha=val
                if alpha>=beta: break

            # TT保存
            flag=0
            if val<=a0: flag=-1
            elif val>=beta: flag=+1
            TT[k]=(depth, flag, val)
            return val

        # 反復深化：浅い→深い。時間切れで最後の確定手を返す
        best_move = None
        cur_depth = 1
        while cur_depth <= 8:  # 盤が小さいので8ply程度まで
            if time_up(): break
            _ = negamax(board, cur_depth, -10**12, 10**12, me)
            if BEST[0] is not None:
                best_move = BEST[0]
            cur_depth += 1
            if time_up(): break

        # 何も見つからなかった保険：最初の合法手
        if not best_move:
            ms = legal_moves(board)
            if ms: best_move = ms[0]
            else:  best_move = (0,0)
        return best_move
