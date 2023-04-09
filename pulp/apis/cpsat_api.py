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
# Users would need to install python OR-Tools CP-SAT on their machine.
# More instructions on: https://developers.google.com/optimization


from pulp.apis.core import LpSolver, PulpSolverError


class CPSAT_PY(LpSolver):
    """The OR-Tools CP-SAT solver"""

    name: str = "CPSAT_PY"

    try:
        global ortools
        import ortools

    except:

        def available(self):
            """True if the solver is available"""
            return False

        def actualSolve(self, lp, callback=None):
            """Solve a well formulated lp problem"""
            raise PulpSolverError("OR-Tools CP-SAT: Not Available")
        
    else:

        @staticmethod
        def isSatProblem(lp):
            """Checks if the problem is a SAT problem"""
            names = set(var.name for var in lp.objective.keys()) - {'__dummy'}
            return len(names) == 0
        
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
            # if an object is specified, warn the user that it is not supported
            if not self.isSatProblem(lp):
                import warnings
                warnings.warn("CPSAT_PY: Objective has terms. CP-SAT supports only SAT problems.")

            raise NotImplementedError

        def findSolutionValues(self, lp):
            raise NotImplementedError
        
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
            raise PulpSolverError("OR-Tools CP-SAT: Resolving is not supported")
