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
import pathlib

from pulp import constants
from .core import LpSolver, PulpSolverError


class Z3Model:
    """z3 objects for a lp model"""
    def __init__(
            self, 
            timeout: int,
            logPath: str,
        ) -> None:
        self.constraints = []
        self.variables = {}
        self.solver = None 
        self.model = None
        self.timeout = timeout
        self.logPath = logPath

    def addVariable(self, variable):
        """add a variable to the model"""
        self.variables[variable.decl().name()] = variable

    def addConstraint(self, constraint):
        """add a constraint to the model"""
        self.constraints.append(constraint)
        
    def getVariable(self, name):
        """get variable from its identifier"""
        return self.variables[name]
    
    def getSolver(self):
        """return a configured Z3 solver"""
        solver = z3.Solver()
        if self.timeout is not None:
            solver.set("timeout", self.timeout)
        if self.logPath is not None:
            logPath = pathlib.Path(self.logPath)
            solver.set("smtlib2_log", str(logPath / "z3.smt2"))
            solver.set("proof.log", str(logPath / "z3.proof"))
        return solver
    
    def solve(self):
        """run the Z3 solver"""
        self.solver = self.getSolver() 
        for constraint in self.constraints:
            self.solver.add(constraint)
        status = self.solver.check()
        if status.r > 0:
            self.model = self.solver.model()
        return self.solver
    
    @property
    def status(self):
        """get the status of the solved model"""
        if self.model is None:
            reason = self.solver.reason_unknown()
            if reason == "timeout":
                return constants.LpStatusNotSolved
            else:
                return constants.LpStatusInfeasible
        return constants.LpStatusOptimal 
    
    def getVariableValue(self, variable):
        """get the value of a variable of solved model"""
        if self.model is None:
            raise RuntimeError("Z3 Model has not been satisfied yet")
        return self.model[variable]


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
            self.logPath = logPath
            super().__init__(mip, msg, timeLimit=timeLimit, **solverParams)

        def available(self):
            """True if the solver is available"""
            return True
        
        def callSolver(self, lp):
            lp.solverModel.solve()
        
        def buildSolverModel(self, lp):
            lp.solverModel = Z3Model(self.timeLimit, self.logPath)
            for var in lp.variables():
                if var.cat == constants.LpInteger:
                    z3Var = z3.Int(var.name)
                elif var.cat == constants.LpContinuous:
                    z3Var = z3.Real(var.name)
                else:
                    raise ValueError(f"Z3: Variable type {var.cat} not supported")
                lp.solverModel.addVariable(z3Var)
                # can we do bounds better than this?
                lp.solverModel.addConstraint(z3Var >= var.lowBound)
                lp.solverModel.addConstraint(z3Var <= var.upBound)
                
            for constraint in lp.constraints.values():
                expr = []
                for v, coefficient in constraint.items():
                    expr.append(coefficient * lp.solverModel.getVariable(v.name))

                rhs = -constraint.constant
                if constraint.sense == constants.LpConstraintEQ:
                    constr = sum(expr) == rhs
                elif constraint.sense == constants.LpConstraintLE:
                    constr = sum(expr) <= rhs
                else:
                    constr = sum(expr) >= rhs
                lp.solverModel.addConstraint(constr)

        def findSolutionValues(self, lp):
            if lp.solverModel.status != constants.LpStatusOptimal:
                return lp.solverModel.status
            else:
                for var in lp.variables():
                    var.varValue = lp.solverModel.model[lp.solverModel.getVariable(var.name)]
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
            raise PulpSolverError("Z3: Resolving is not supported")
