# PuLP : Python LP Modeler
# Version 2.4

# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE."""

# Implemented by Ethan Lew (@EthanJamesLew on Github)
# Users would need to install Z3 and the Python bindings (z3-solver on PyPI) on their machine and provide the path to the executable.
# More instructions on: https://github.com/Z3Prover/z3

from pulp import constants
from .core import LpSolver, PulpSolverError


class Z3_PY(LpSolver):
    """The Z3 solver"""

    name: str = "Z3_PY"

    try:
        global z3
        import z3

    except:

        def available(self):
            """True if the solver is available"""
            return False

        def actualSolve(self, lp, callback=None):
            """Solve a well formulated lp problem"""
            raise PulpSolverError("Z3: Not Available")
    
    else:
        
        def __init__(
            self,
            mip=True,
            msg=True,
            timeLimit=None,
            warmStart=False,
            logPath=None,
            **solverParams,
        ):
            super().__init__(mip, msg, timeLimit=timeLimit, **solverParams)

        def available(self):
            """True if the solver is available"""
            return True
        
        def callSolver(self, lp):
            z3Solver = z3.Solver()
            for constraint in lp.constraints.values():
                z3Solver.add(constraint.z3Constraint)
            z3Solver.check()
            lp.Z3SolveStatus = z3Solver
        
        def buildSolverModel(self, lp):
            # TODO: make a model context so these variables aren't added to LpModel items
            for var in lp.variables():
                if var.cat == constants.LpInteger:
                    var.z3Var = z3.Int(var.name)
                elif var.cat == constants.LpContinuous:
                    var.z3Var = z3.Real(var.name)
                else:
                    raise ValueError("Z3: Variable type not supported")
                
            for _, constraint in lp.constraints.items():
                expr = []
                for v, coefficient in constraint.items():
                    expr.append(coefficient * v.z3Var)

                rhs = -constraint.constant
                if constraint.sense == constants.LpConstraintEQ:
                    constraint.z3Constraint = z3.Sum(expr) == rhs 
                elif constraint.sense == constants.LpConstraintLE:
                    constraint.z3Constraint = z3.Sum(expr) <= rhs 
                else:
                    constraint.z3Constraint = z3.Sum(expr) >= rhs 

        def findSolutionValues(self, lp):
            model = lp.Z3SolveStatus.model()
            for var in lp.variables():
                var.varValue = model[var.z3Var]
            # TODO: get the status
            # TODO: this really shouldn't be optimal, but feasible
            return constants.LpStatusOptimal
        
        def actualSolve(self, lp):
            self.buildSolverModel(lp)
            self.callSolver(lp)

            solutionStatus = self.findSolutionValues(lp)

            for var in lp.variables():
                var.modified = False

            for constraint in lp.constraints.values():
                constraint.modifier = False

            return solutionStatus
        
        def actualResolve(self, lp, **kwargs):
            raise NotImplementedError