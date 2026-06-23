"""
server.jl — LaTeX Calculator Heavy Compute Fallback Engine
===========================================================
A local HTTP server that receives LaTeX expressions from the browser
frontend and evaluates them using native Julia/Python SymPy at full
machine speed — bypassing the WebAssembly performance ceiling of Pyodide.

REQUIRED PACKAGES (install once with the Julia REPL):
─────────────────────────────────────────────────────
  julia> using Pkg
  julia> Pkg.add(["HTTP", "JSON3", "SymPy", "Roots"])

Note on SymPy.jl:
  SymPy.jl calls CPython via PyCall.jl. It requires a working Python
  installation with SymPy installed. On first use, Julia will ask to
  configure PyCall. Ensure your system Python has SymPy installed:
    \$ pip install sympy antlr4-python3-runtime==4.11

RUNNING THE SERVER:
───────────────────
  \$ julia server.jl
  Server listening on http://127.0.0.1:8001

  The browser frontend routes timed-out expressions to this server
  when the user clicks "Run via Julia" in the inline timeout prompt.

DEVELOPMENT TIP:
  Run with `julia --project=. server.jl` if you use a local Project.toml.

API:
────
  POST /solve
    Body:    { "expression": "<LaTeX string>" }
    Returns: { "result": "<LaTeX string>", "method": "symbolic" | "numeric" }
         or  { "error": "<message>" }

  GET /health
    Returns: { "status": "ok", "engine": "Julia + SymPy" }
"""

using HTTP
using JSON3
using SymPy
using PyCall
using Roots
using Printf

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

const HOST = "127.0.0.1"
const PORT = 8001

# CORS headers — required so the browser (served on a different port) can
# POST here without triggering a CORS policy block.
const CORS_HEADERS = [
    "Access-Control-Allow-Origin"  => "*",
    "Access-Control-Allow-Methods" => "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers" => "Content-Type, Accept",
    "Content-Type"                 => "application/json",
]


# ─────────────────────────────────────────────────────────────────────────────
# JSON helpers
# ─────────────────────────────────────────────────────────────────────────────

json_ok(d::AbstractDict)                  = HTTP.Response(200, CORS_HEADERS; body=JSON3.write(d))
json_err(msg::AbstractString, code=500)   = HTTP.Response(code, CORS_HEADERS; body=JSON3.write(Dict("error" => msg)))


# ─────────────────────────────────────────────────────────────────────────────
# Expression-type sniffer
# ─────────────────────────────────────────────────────────────────────────────

"""
    detect_expr_type(latex) -> Symbol

Classify the dominant structure of a LaTeX expression. Used for logging
and for the solver-routing hints injected into the Python dispatcher.

Returns one of: :integral, :sum, :product, :limit, :ode, :equation, :expression
"""
function detect_expr_type(latex::AbstractString)::Symbol
    occursin(r"\\frac\{d[^{}]*\}\{d[^{}]+\}", latex) && return :ode
    occursin(raw"\int",  latex) && return :integral
    occursin(raw"\sum",  latex) && return :sum
    occursin(raw"\prod", latex) && return :product
    occursin(raw"\lim",  latex) && return :limit
    occursin("=",        latex) && !occursin(r"\\begin|\\end", latex) && return :equation
    return :expression
end


# ─────────────────────────────────────────────────────────────────────────────
# Core evaluation engine (Python bridge via SymPy.jl / PyCall)
# ─────────────────────────────────────────────────────────────────────────────

"""
    evaluate_expression(latex) -> (result_latex, method)

Parse the incoming LaTeX string via CPython's sympy.parsing.latex,
evaluate/simplify using SymPy's full solver suite, and convert the
result back to a LaTeX string.

Solver cascade (in priority order):
  1. parse_latex → expr.doit() → simplify()
     Handles integrals, sums, limits, derivatives directly.
  2. sympy.solve()  for equations with free symbols.
  3. sympy.dsolve() for ODEs.
  4. sympy.N()      for numerical evaluation (fallback, method="numeric").

Throws on unrecoverable parse or evaluation errors.
"""
function evaluate_expression(latex::AbstractString)::Tuple{String,String}

# ─────────────────────────────────────────────────────────────────────────────
# Python SymPy Bridge Setup
# ─────────────────────────────────────────────────────────────────────────────

py"""
import sympy
from sympy import (
    simplify, Symbol, N, dsolve, solve,
    latex as to_latex, Derivative, Eq, FiniteSet
)
from sympy.parsing.latex import parse_latex
from sympy.parsing.latex.errors import LaTeXParsingError
import re

GLOBAL_STATE = {}

def _solve_dispatch(latex_str, use_state=False):
    # ── 0. Pre-process ──────────────────────────────────────────────────────
    # Convert \frac{\partial}{\partial x} -> \frac{d}{d x}
    latex_str = re.sub(r'\\frac\{\\partial\}\{\\partial\s*([a-zA-Z])\}', r'\\frac{d}{d \g<1>}', latex_str)

    # ── 1. Parse ────────────────────────────────────────────────────────────
    expr = None

    if "=" in latex_str:
        parts = latex_str.split("=", 1)
        lhs_str, rhs_str = parts[0].strip(), parts[1].strip()
        if lhs_str and rhs_str:
            try:
                lhs_parsed = parse_latex(lhs_str)
                rhs_parsed = parse_latex(rhs_str)
                
                # Check for variable assignment A = ...
                if use_state and isinstance(lhs_parsed, sympy.Symbol):
                    if rhs_parsed is not None:
                        rhs_eval = rhs_parsed.doit()
                        if use_state:
                            GLOBAL_STATE[lhs_parsed] = rhs_eval
                        return f"{to_latex(lhs_parsed)} = {to_latex(rhs_eval)}", "assignment"

                if lhs_parsed is not None and rhs_parsed is not None:
                    # We inject pi, e, i manually since the server.jl injects later
                    fs = (lhs_parsed - rhs_parsed).free_symbols
                    subs = {}
                    if sympy.Symbol('pi') in fs: subs[sympy.Symbol('pi')] = sympy.pi
                    if sympy.Symbol('e')  in fs: subs[sympy.Symbol('e')]  = sympy.E
                    if sympy.Symbol('i')  in fs: subs[sympy.Symbol('i')]  = sympy.I
                    
                    lhs_parsed = lhs_parsed.subs(subs)
                    rhs_parsed = rhs_parsed.subs(subs)
                    equation_expr = lhs_parsed - rhs_parsed
                    equation_expr = equation_expr.doit()
                    
                    free = list(equation_expr.free_symbols)
                    if free:
                        var = free[0]
                        if sympy.Symbol('y') in free and sympy.Symbol('x') in free:
                            var = sympy.Symbol('y')
                        try:
                            sols = sympy.solve(equation_expr, var)
                            if isinstance(sols, list) and len(sols) == 0:
                                raise ValueError("Empty")
                            if isinstance(sols, list):
                                formatted_sols = ", ".join([to_latex(s) for s in sols])
                                if len(sols) == 1:
                                    latex_str = f"{to_latex(var)} = {formatted_sols}"
                                else:
                                    latex_str = f"{to_latex(var)} \\in \\left\\{{ {formatted_sols} \\right\\}}"
                                return latex_str, "equation"
                        except Exception:
                            try:
                                nsol = sympy.nsolve(equation_expr, var, 1.0)
                                return f"{to_latex(var)} \\approx {to_latex(nsol)}", "numeric"
                            except Exception:
                                raise ValueError("Cannot evaluate: No symbolic closed form")
            except ValueError as ve:
                if "No symbolic closed form" in str(ve):
                    raise ve
            except Exception:
                pass

    # First try parsing as a matrix environment
    m = re.fullmatch(r'\\begin\{(bmatrix|pmatrix|vmatrix|matrix)\}(.*?)\\end\{\1\}', latex_str.strip(), flags=re.DOTALL)
    if m:
        mat_type = m.group(1)
        content = m.group(2)
        rows_str = [r for r in content.split(r'\\') if r.strip()]
        rows = []
        try:
            for r in rows_str:
                cols_str = r.split('&')
                rows.append([parse_latex(c.strip()) for c in cols_str])
            if rows:
                expr = sympy.Matrix(rows)
                if mat_type == 'vmatrix':
                    expr = sympy.det(expr)
        except Exception:
            pass # fall through to default parser if matrix parsing fails

    if expr is None:
        try:
            expr = parse_latex(latex_str)
            if hasattr(expr, 'doit'):
                expr = expr.doit()
        except LaTeXParsingError as exc:
            raise ValueError(f"LaTeX parse error: {exc}") from exc
        except Exception as exc:
            raise ValueError(f"Parse error: {exc}") from exc

    # ── 2. Inject standard mathematical constants and global state ───────────
    fs   = expr.free_symbols
    subs = {}
    if Symbol('pi') in fs: subs[Symbol('pi')] = sympy.pi
    if Symbol('e')  in fs: subs[Symbol('e')]  = sympy.E
    if Symbol('i')  in fs: subs[Symbol('i')]  = sympy.I
    if use_state:
        for s in fs:
            if s in GLOBAL_STATE:
                subs[s] = GLOBAL_STATE[s]
    if subs:
        expr = expr.subs(subs)

    result = None
    method = "symbolic"

    # ── 3a. doit() handles integrals, sums, limits, derivatives ─────────────
    try:
        evaled     = expr.doit()
        
        # Force expansion for generic polynomial benchmark payloads
        expanded = sympy.expand(evaled)
        if expanded != expr:
            result = expanded
        else:
            simplified = simplify(evaled)
            if simplified != expr:
                result = simplified
    except NotImplementedError:
        pass   # no closed form — fall through to further solvers
    except Exception:
        pass

    # ── 3a-ii. Definite-integral numeric fallback ────────────────────────────
    # If doit() returned something that still contains an unevaluated integral
    # (or the result equals the input), and the expression has NO free symbolic
    # variables (meaning it's fully numeric), force a numerical evaluation.
    if result is None or (result is not None and
       to_latex(result).count(r'\int') > 0 and
       not result.free_symbols - {sympy.pi, sympy.E, sympy.I}):
        try:
            target = result if result is not None else expr
            numeric = target.evalf(15, quad=True)
            # Only accept if it's a genuine float (no remaining symbols)
            if not numeric.free_symbols:
                result = numeric
                method = "numeric"
        except Exception:
            pass

    # ── 3b. Equation solver: solve(lhs - rhs, var) ───────────────────────────
    if result is None:
        free = list(expr.free_symbols - {sympy.pi, sympy.E, sympy.I})
        if hasattr(expr, 'lhs') and hasattr(expr, 'rhs') and free:
            try:
                sols = solve(expr, free[0])
                if sols:
                    result = FiniteSet(*sols)
            except Exception:
                pass
        # Do not automatically solve expr = 0 for generic polynomials 
        # unless it was an explicit equation, to avoid converting 
        # (x+y+z)^25 into {-y - z}.

    # ── 3c. ODE solver ───────────────────────────────────────────────────────
    if result is None and expr.has(Derivative):
        try:
            sol    = dsolve(expr)
            result = sol
        except Exception:
            pass

    # ── 4. Numerical fallback ────────────────────────────────────────────────
    if result is None or result == expr:
        try:
            target = expr if result is None else result
            numeric = target.evalf(15, quad=True)
            if not numeric.free_symbols:
                result = numeric
                method = "numeric"
            else:
                result = target # keep symbolic if it couldn't fully evaluate
        except Exception:
            result = expr if result is None else result

    # Convert to latex
    latex_res = to_latex(result)
    
    return latex_res, method
"""

# ─────────────────────────────────────────────────────────────────────────────
# Core evaluation engine
# ─────────────────────────────────────────────────────────────────────────────

function evaluate_expression(latex::AbstractString, use_state::Bool=false)::Tuple{String,String}
    tup = py"_solve_dispatch"(latex, use_state)
    return String(tup[1]), String(tup[2])
end


# ─────────────────────────────────────────────────────────────────────────────
# Julia-native Roots.jl numerical fallback
# ─────────────────────────────────────────────────────────────────────────────

"""
    roots_fallback(latex) -> (result_latex, method)

Last-resort numerical root-finder using Roots.jl.
Called when the Python/SymPy dispatcher signals a pure failure by throwing.

Converts the expression to a Julia callable via SymPy.jl's lambdify
interface and finds roots in the domain [-1e6, 1e6] using Bisection.
"""
function roots_fallback(latex::AbstractString)::Tuple{String,String}
    # Parse with SymPy.jl (Julia-side API)
    expr_sym = sympy.parse_latex(latex)
    free     = collect(expr_sym.free_symbols)

    isempty(free) && error("No free variables for numerical solve.")

    var = first(free)
    f   = lambdify(expr_sym, [var])   # SymPy.jl utility — returns a Julia Function

    # Search for a sign change in [-1e6, 1e6] as a bracket
    a, b = -1e6, 1e6
    try
        root = find_zero(f, (a, b), Bisection(); xatol=1e-12)
        result = @sprintf("%.12g", root)
        return result, "numeric (Roots.jl)"
    catch
        # Attempt a derivative-free method from a heuristic start point
        root = find_zero(f, 0.0; xatol=1e-12)
        result = @sprintf("%.12g", root)
        return result, "numeric (Roots.jl)"
    end
end


# ─────────────────────────────────────────────────────────────────────────────
# Combined evaluation with Roots.jl safety net
# ─────────────────────────────────────────────────────────────────────────────

"""
    safe_evaluate(latex) -> (result_latex, method)

Wraps evaluate_expression with a Roots.jl safety net.
Order of attempts:
  1. SymPy symbolic/numeric (Python bridge).
  2. Roots.jl bisection / derivative-free root finder.
"""
function safe_evaluate(latex::AbstractString, use_state::Bool=false)::Tuple{String,String}
    try
        return evaluate_expression(latex, use_state)
    catch sympy_err
        @warn "SymPy failed, trying Roots.jl numerical fallback" error=sprint(showerror, sympy_err)
        try
            return roots_fallback(latex)
        catch roots_err
            # Re-throw the original SymPy error — it's more informative.
            rethrow(sympy_err)
        end
    end
end


# ─────────────────────────────────────────────────────────────────────────────
# HTTP request handlers
# ─────────────────────────────────────────────────────────────────────────────

handle_options(::HTTP.Request) = HTTP.Response(204, CORS_HEADERS)

function handle_health(::HTTP.Request)
    json_ok(Dict(
        "status" => "ok",
        "engine" => "Julia + SymPy.jl + Roots.jl",
        "port"   => PORT,
    ))
end

function handle_solve(req::HTTP.Request)
    try
        # ── Parse body ──────────────────────────────────────────────────────────
        body = try
            JSON3.read(req.body)
        catch
            return json_err("Invalid JSON body.", 400)
        end

        raw = get(body, :expression, nothing)
        isnothing(raw) && return json_err("Missing 'expression' field.", 400)

        latex = strip(String(raw))
        isempty(latex)           && return json_err("Empty expression.", 400)
        length(latex) > 5_000    && return json_err("Expression too long (max 5000 chars).", 400)

        expr_type = detect_expr_type(latex)
        @info "→ Solve request" type=expr_type expression=first(latex, 120)

        use_state = get(body, :persistent, false)
        
        # ── Evaluate with 20-second hard guardrail ───────────────────────────────
        TIMEOUT_SECS = 20
        result_ch = Channel{Union{Tuple{String,String}, Exception}}(1)

        task = @async begin
            try
                put!(result_ch, safe_evaluate(latex, use_state))
            catch err
                put!(result_ch, err)
            end
        end

        # Wait up to TIMEOUT_SECS for a result
        timed_out = timedwait(() -> isready(result_ch), TIMEOUT_SECS; pollint=0.2) == :timed_out

        if timed_out
            @warn "✗ Julia engine timed out after $(TIMEOUT_SECS)s" expression=first(latex, 120)
            return HTTP.Response(408, CORS_HEADERS;
                body = JSON3.write(Dict(
                    "error" => "Julia Engine Terminated: Calculation exceeded the $(TIMEOUT_SECS)s time limit."
                ))
            )
        end

        outcome = take!(result_ch)

        if outcome isa Exception
            msg = sprint(showerror, outcome)
            @warn "✗ Evaluation failed" error=msg
            return HTTP.Response(500, CORS_HEADERS; body = JSON3.write(Dict("status" => "error", "error" => "Julia Engine Error: " * msg)))
        end

        result_latex, method = outcome

        @info "✓ Success" method=method result=first(result_latex, 120)

        return json_ok(Dict(
            "result" => result_latex,
            "method" => method,
        ))
    catch e
        msg = sprint(showerror, e)
        @error "Fatal error in handle_solve" exception=(e, catch_backtrace())
        return HTTP.Response(500, CORS_HEADERS; body = JSON3.write(Dict("status" => "error", "error" => "Julia Engine Error: " * msg)))
    end
end


function handle_solve_batch(req::HTTP.Request)
    try
        body = try
            JSON3.read(req.body)
        catch
            return json_err("Invalid JSON body.", 400)
        end

        raw = get(body, :expressions, nothing)
        isnothing(raw) && return json_err("Missing 'expressions' field.", 400)

        use_state = get(body, :persistent, false)

        results = String[]
        for raw_expr in raw
            latex = strip(String(raw_expr))
            if isempty(latex) || length(latex) > 5_000
                push!(results, "Error: Invalid expression length")
                continue
            end

            try
                result_latex, method = safe_evaluate(latex, use_state)
                push!(results, result_latex)
            catch e
                msg = sprint(showerror, e)
                push!(results, "Error: " * msg)
            end
        end

        return HTTP.Response(200, CORS_HEADERS; body=JSON3.write(results))
    catch e
        msg = sprint(showerror, e)
        @error "Fatal error in handle_solve_batch" exception=(e, catch_backtrace())
        return HTTP.Response(500, CORS_HEADERS; body = JSON3.write(Dict("status" => "error", "error" => "Julia Engine Error: " * msg)))
    end
end


# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────

function router(req::HTTP.Request)::HTTP.Response
    m, p = req.method, req.target
    m == "OPTIONS"              && return handle_options(req)
    m == "GET"  && p == "/health" && return handle_health(req)
    m == "POST" && p == "/solve"  && return handle_solve(req)
    m == "POST" && p == "/solve_batch" && return handle_solve_batch(req)
    return json_err("Not found: $m $p", 404)
end


# ─────────────────────────────────────────────────────────────────────────────
# Startup
# ─────────────────────────────────────────────────────────────────────────────

function main()
    @info """
    ╔══════════════════════════════════════════════════════════╗
    ║   LaTeX Calc — Julia Heavy Compute Engine  v1.0         ║
    ║   http://$(HOST):$(PORT)                                ║
    ╠══════════════════════════════════════════════════════════╣
    ║   POST /solve   →  evaluate a LaTeX expression           ║
    ║   GET  /health  →  liveness probe                        ║
    ╠══════════════════════════════════════════════════════════╣
    ║   Required packages: HTTP, JSON3, SymPy, Roots           ║
    ║   Install:  julia> Pkg.add(["HTTP","JSON3","SymPy","Roots"])║
    ╚══════════════════════════════════════════════════════════╝
    Press Ctrl+C to stop.
    """

    HTTP.serve(router, HOST, PORT;
        reuseaddr = true,   # Quick restart without "port in use" errors
        verbose   = false,  # We do our own @info logging in each handler
    )
end

main()
