import sys
sys.path.insert(0, '.')
from latex_calculator import evaluate_latex

s = r'\begin{vmatrix} a & b \\ c & d \end{vmatrix}'
print(evaluate_latex(s, '{}'))
