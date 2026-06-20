import sys
sys.path.insert(0, '.')
from latex_calculator import _try_matrix

s = r'\begin{vmatrix} a & b \\ c & d \end{vmatrix}'
print(_try_matrix(s))
