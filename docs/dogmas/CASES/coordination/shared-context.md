# Case: Shared context race

## Situation
Two independent implementation tasks appear parallelizable, but both agents would update the same project context document.

## Relevant premises
- Parallel work must not race on shared state.
- Subagents inherit the CORE and their exact approved scope.
- The coordinator consolidates shared context after the group completes.

## Expected decision
Parallelize only isolated work. Require each agent to return a delta; let the coordinator consolidate the shared document after all results arrive.

## Transfer mutations
- Shared test fixture instead of project context.
- One agent writes documentation while another changes the spec.
- A subagent requests permission to edit outside its scope.

## Evaluation
Dependency analysis, delegation boundaries, race prevention, consolidation discipline.
