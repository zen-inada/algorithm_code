from typing import Tuple
from framework import Alg3D, Board
import time

class MyAI(Alg3D):
    def get_move(self, board: Board) -> Tuple[int, int]:
        T_SOFT = 2.4  # CPU制限3秒の安全側
        t0 = time.perf_counter()

        # --- 基本 ---
        def count_stones(b):
            c1=c2=0
            for z in range(4):
                for y in range(4):
                    for x in range(4):
                        v=b[z][y][x]
                        if v==1: c1+=1
                        elif v==2: c2+=1
            return c1,c2

        c1,c2 = count_stones(board)
        me = 1 if c1==c2 else 2
        opp = 3 - me

        def legal_moves(b):
            ms=[]
            for y in range(4):
                for x in range(4):
                    if b[3][y][x]==0:
                        ms.append((x,y))
            ms.sort(key=lambda m: abs(m[0]-1.5)+abs(m[1]-1.5))
            return ms

        def drop_z(b,x,y):
            for z in range(4):
                if b[z][y][x]==0: return z
            return None

        # --- 勝ちライン生成 ---
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
                            else: break
                        if len(line)==4: LINES.append(line)

        def is_win(b,player):
            for line in LINES:
                if all(b[z][y][x]==player for (x,y,z) in line):
                    return True
            return False

        W = [0,1,4,32,10000]
        def eval_board(b):
            if is_win(b,me): return 10**9
            if is_win(b,opp): return -10**9
            score=0
            heights=[[0]*4 for _ in range(4)]
            for y in range(4):
                for x in range(4):
                    h=0
                    for z in range(4):
                        if b[z][y][x]!=0: h=z+1
                    heights[y][x]=h
            for line in LINES:
                cm=co=0; feas=0
                for (x,y,z) in line:
                    v=b[z][y][x]
                    if v==me: cm+=1
                    elif v==opp: co+=1
                    else:
                        if heights[y][x]<=z: feas+=1
                if cm and co: continue
                if cm: score += W[cm]+feas
                elif co: score -= W[co]+feas
            return score

        def do_move(b,x,y,player):
            z=drop_z(b,x,y)
            b[z][y][x]=player
            return z
        def undo_move(b,x,y,z): b[z][y][x]=0

        # 即勝ち or ブロック
        def tactical(b):
            for (x,y) in legal_moves(b):
                z=drop_z(b,x,y); b[z][y][x]=me
                if is_win(b,me): b[z][y][x]=0; return (x,y)
                b[z][y][x]=0
            for (x,y) in legal_moves(b):
                z=drop_z(b,x,y); b[z][y][x]=opp
                if is_win(b,opp): b[z][y][x]=0; return (x,y)
                b[z][y][x]=0
            return None

        tact=tactical(board)
        if tact: return tact

        TT={}
        BEST=(None,-10**12)
        cur_depth=1

        def time_up(): return (time.perf_counter()-t0)>=T_SOFT

        def negamax(b,depth,alpha,beta,turn):
            if time_up(): return eval_board(b)
            k=(tuple(v for z in b for y in z for v in y),turn)
            if k in TT and TT[k][0]>=depth:
                flag,val=TT[k][1],TT[k][2]
                if flag==0: return val
                if flag>0 and val>alpha: alpha=val
                elif flag<0 and val<beta: beta=val
                if alpha>=beta: return val
            if depth==0: return eval_board(b)
            moves=legal_moves(b)
            if not moves: return eval_board(b)
            ordered=[]
            for (x,y) in moves:
                z=drop_z(b,x,y); b[z][y][x]=turn
                sc=0
                if is_win(b,turn): sc+=10**7
                b[z][y][x]=0
                sc-= (abs(x-1.5)+abs(y-1.5))*10
                ordered.append((sc,x,y))
            ordered.sort(reverse=True)
            val=-10**12
            nxt=3-turn; a0=alpha
            for _,x,y in ordered:
                z=do_move(b,x,y,turn)
                v=-negamax(b,depth-1,-beta,-alpha,nxt)
                undo_move(b,x,y,z)
                if v>val:
                    val=v
                    if turn==me and depth==cur_depth and v>BEST[1]:
                        nonlocal BEST
                        BEST=((x,y),v)
                if val>alpha: alpha=val
                if alpha>=beta: break
            flag=0
            if val<=a0: flag=-1
            elif val>=beta: flag=+1
            TT[k]=(depth,flag,val)
            return val

        best=None
        while cur_depth<=8:
            if time_up(): break
            _=negamax(board,cur_depth,-10**12,10**12,me)
            if BEST[0] is not None: best=BEST[0]
            cur_depth+=1
            if time_up(): break
        if not best:
            ms=legal_moves(board)
            best=ms[0] if ms else (0,0)
        return best
