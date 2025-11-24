"""
Consistency checker for StageFlow process validation.

This module provides intelligent cycle detection and classification for process definitions,
distinguishing between safe controlled cycles and problematic ones.
"""


from stageflow.models import ProcessDefinition
from stageflow.models.consistency import (
    ConsistencyIssue,
    ProcessIssueTypes,
    TerminationAnalysis,
)


class ProcessConsistencyChecker:
    """Enhanced consistency checker with intelligent cycle detection."""

    def __init__(self, process_def: ProcessDefinition):
        self.process_def = process_def
        self.issues: list[ConsistencyIssue] = []
        self.check_consistency()

    @property
    def valid(self) -> bool:
        """Indicate if the process is consistent."""
        return len(self.issues) == 0

    def check_consistency(self) -> None:
        """Perform all consistency checks on the process definition."""
        self._check_invalid_transitions()
        self._check_self_referencing_gates()
        self._check_circular_dependencies()
        self._check_multiple_gates_same_target()
        self._check_logical_conflicts()
        # Other checks can be added here

    def _check_invalid_transitions(self) -> None:
        """Identify transitions to non-existent stages."""
        stages = self.process_def.get("stages", {})
        if not isinstance(stages, dict):
            return  # Skip if stages is not a dict
        stage_ids = set(stages.keys())
        for stage_name, stage in stages.items():
            if not isinstance(stage, dict):
                continue
            gates = stage.get("gates", {})
            if not isinstance(gates, dict):
                continue
            for gate_name, gate in gates.items():
                if not isinstance(gate, dict):
                    continue
                target = gate.get("target_stage")
                if isinstance(target, str) and target not in stage_ids:
                    issue = ConsistencyIssue(
                        issue_type=ProcessIssueTypes.INVALID_TRANSITION,
                        description=f"Gate '{gate_name}' in stage '{stage_name}' targets non-existent stage '{target}'",
                        stages=[stage_name, target],
                    )
                    self.issues.append(issue)

    def _check_self_referencing_gates(self) -> None:
        """Check for self-referencing gates (always FATAL)."""
        stages = self.process_def.get("stages", {})
        if not isinstance(stages, dict):
            return
        for stage_name, stage in stages.items():
            if not isinstance(stage, dict):
                continue
            gates = stage.get("gates", {})
            if not isinstance(gates, dict):
                continue
            for gate_name, gate in gates.items():
                if not isinstance(gate, dict):
                    continue
                target = gate.get("target_stage")
                if isinstance(target, str) and target == stage_name:
                    issue = ConsistencyIssue(
                        issue_type=ProcessIssueTypes.SELF_REFERENCING_GATE,
                        description=f"Gate '{gate_name}' in stage '{stage_name}' references the same stage, creating an infinite self-loop",
                        stages=[stage_name],
                    )
                    self.issues.append(issue)

    def _check_circular_dependencies(self) -> None:
        """Enhanced cycle detection with intelligent classification.

        This method replaces the old blanket rejection of all cycles with
        intelligent analysis that classifies cycles based on:
        1. Self-loops (always FATAL - handled separately)
        2. Exit path to final stage (FATAL if missing)
        3. Termination conditions in gate locks (WARNING if unclear)
        """

        # Detect all cycles using DFS algorithm
        cycles = self._detect_all_cycles()

        if not cycles:
            return  # No cycles to analyze

        # Analyze each cycle for exit paths and termination
        for cycle_path in cycles:
            # Check if cycle has any exit path to final stage
            has_exit = self._cycle_has_path_to_final(cycle_path)

            if not has_exit:
                # FATAL: Guaranteed infinite loop with no escape
                self._report_infinite_cycle(cycle_path)
                continue

            # Cycle has exit path - analyze locks for termination conditions
            termination_analysis = self._analyze_cycle_termination(cycle_path)

            if termination_analysis.has_termination:
                # Cycle is controlled - optionally report for visibility
                if self._should_report_controlled_cycles():
                    self._report_controlled_cycle(cycle_path, termination_analysis)
            else:
                # WARNING: Cannot verify termination conditions
                self._report_uncontrolled_cycle(cycle_path, termination_analysis)

    def _detect_all_cycles(self) -> list[list[str]]:
        """Detect all cycles in the process using DFS.

        Returns:
            List of cycle paths, where each path is a list of stage IDs
        """
        cycles: list[list[str]] = []
        visited: set[str] = set()
        rec_stack: set[str] = set()
        path: list[str] = []

        def dfs(stage_id: str) -> None:
            visited.add(stage_id)
            rec_stack.add(stage_id)
            path.append(stage_id)

            stages = self.process_def.get("stages", {})
            if not isinstance(stages, dict):
                path.pop()
                rec_stack.remove(stage_id)
                return

            stage = stages.get(stage_id)
            if not isinstance(stage, dict):
                path.pop()
                rec_stack.remove(stage_id)
                return

            gates = stage.get("gates", {})
            if not isinstance(gates, dict):
                path.pop()
                rec_stack.remove(stage_id)
                return

            # Check all outgoing transitions
            for gate in gates.values():
                if not isinstance(gate, dict):
                    continue
                target = gate.get("target_stage")
                if not isinstance(target, str):
                    continue

                if target not in visited:
                    dfs(target)
                elif target in rec_stack:
                    # Found a cycle - extract it from current path
                    cycle_start = path.index(target)
                    cycle = path[cycle_start:] + [target]
                    cycles.append(cycle)

            path.pop()
            rec_stack.remove(stage_id)

        # Check each stage
        stages = self.process_def.get("stages", {})
        if isinstance(stages, dict):
            for stage_id in stages:
                if isinstance(stage_id, str) and stage_id not in visited:
                    dfs(stage_id)

        return cycles

    def _cycle_has_path_to_final(self, cycle_path: list[str]) -> bool:
        """Check if any stage in the cycle has a path to the final stage.

        Args:
            cycle_path: List of stage IDs forming the cycle

        Returns:
            True if at least one stage can reach final stage, False otherwise
        """
        final_stage_id = self.process_def.get("final_stage")
        if not isinstance(final_stage_id, str):
            return False

        # Check each stage in cycle for a path to final
        for stage_id in cycle_path[:-1]:  # Exclude duplicate last element
            if self._has_path_to_stage(stage_id, final_stage_id, visited=set(cycle_path)):
                return True

        return False

    def _has_path_to_stage(
        self, from_stage: str, to_stage: str, visited: set[str]
    ) -> bool:
        """Check if there's a path from one stage to another.

        Args:
            from_stage: Starting stage ID
            to_stage: Target stage ID
            visited: Set of already visited stages to avoid cycles

        Returns:
            True if path exists, False otherwise
        """
        if from_stage == to_stage:
            return True

        stages = self.process_def.get("stages", {})
        if not isinstance(stages, dict):
            return False

        stage = stages.get(from_stage)
        if not isinstance(stage, dict):
            return False

        gates = stage.get("gates", {})
        if not isinstance(gates, dict):
            return False

        # Check all gates from this stage
        for gate in gates.values():
            if not isinstance(gate, dict):
                continue
            target = gate.get("target_stage")
            if not isinstance(target, str):
                continue

            # Skip if already visited (avoid infinite loops)
            if target in visited:
                continue

            # Mark as visited and recurse
            new_visited = visited | {target}
            if self._has_path_to_stage(target, to_stage, new_visited):
                return True

        return False

    def _analyze_cycle_termination(self, cycle_path: list[str]) -> TerminationAnalysis:
        """Analyze termination conditions for a cycle.

        Applies multiple detection strategies in order:
        1. Individual lock analysis
        2. Common property analysis (KEY INNOVATION)
        3. Complementary gate analysis

        Args:
            cycle_path: List of stage IDs forming the cycle

        Returns:
            TerminationAnalysis with comprehensive results
        """
        # Get gates that create/maintain this cycle
        cycle_gates = self._get_cycle_gates(cycle_path)

        # Strategy 1: Check individual locks for termination patterns
        individual_analysis = self._analyze_individual_locks(cycle_gates)
        if individual_analysis.has_termination:
            return individual_analysis

        # Strategy 2: Check for common properties with varying requirements (KEY INNOVATION)
        common_prop_analysis = self._analyze_common_properties(cycle_gates)
        if common_prop_analysis.has_termination:
            return common_prop_analysis

        # Strategy 3: Check for complementary gates
        complementary_analysis = self._analyze_complementary_gates(cycle_gates)
        if complementary_analysis.has_termination:
            return complementary_analysis

        # No termination detected
        return TerminationAnalysis(
            has_termination=False,
            termination_type="uncontrolled",
            description="No clear termination conditions detected in cycle gates",
            common_properties=[],
            suggestions=self._generate_termination_suggestions(cycle_gates),
        )

    def _should_report_controlled_cycles(self) -> bool:
        """Whether to report controlled cycles at INFO level.

        This can be made configurable via a flag in the future.
        For now, we don't report controlled cycles to avoid noise.

        Returns:
            False - don't report controlled cycles by default
        """
        return False

    def _get_cycle_gates(self, cycle_path: list[str]) -> list[dict]:
        """
        Get all gates that create or maintain a cycle.

        A gate creates/maintains a cycle if its target_stage points to an earlier
        stage in the cycle path. These are the gates that need to be analyzed for
        termination conditions.

        Args:
            cycle_path: List of stage IDs forming the cycle (e.g., ['A', 'B', 'C', 'A'])
                       Note: The last element is a duplicate of the first (cycle notation)

        Returns:
            List of gate dictionaries that point backward in the cycle

        Example:
            >>> cycle_path = ['processing', 'retry', 'processing']
            >>> gates = self._get_cycle_gates(cycle_path)
            >>> # Returns gates that point from 'retry' back to 'processing'
        """
        cycle_gates = []

        stages = self.process_def.get("stages", {})
        if not isinstance(stages, dict):
            return cycle_gates

        # Iterate through stages in cycle (exclude last element - it's a duplicate)
        for i, stage_id in enumerate(cycle_path[:-1]):
            stage = stages.get(stage_id)
            if not isinstance(stage, dict):
                continue

            gates = stage.get("gates", {})
            if not isinstance(gates, dict):
                continue

            # Check each gate in this stage
            for gate in gates.values():
                if not isinstance(gate, dict):
                    continue
                target_stage = gate.get("target_stage")
                if not isinstance(target_stage, str):
                    continue

                # Does this gate point to an earlier stage in the cycle?
                # Check if target appears before or at current position in cycle path
                if target_stage in cycle_path[:i+1]:
                    cycle_gates.append(gate)
                    # Note: We don't break here because a stage might have multiple
                    # gates that create/maintain the cycle

        return cycle_gates

    def _check_termination_lock(
        self, lock: dict, gate: dict
    ) -> TerminationAnalysis | None:
        """
        Check if a single lock provides a termination condition.

        Detectable patterns:
        - Counter upper bound: LESS_THAN or LESS_THAN_OR_EQUAL with numeric constant
        - Counter lower bound: GREATER_THAN or GREATER_THAN_OR_EQUAL with numeric constant
        - Range boundary: RANGE with numeric [min, max]
        - Finite state set: IN_LIST (deferred to complementary gate check)

        Args:
            lock: Lock dictionary to analyze
            gate: Gate dictionary containing the lock (for context)

        Returns:
            TerminationAnalysis if termination detected, None otherwise

        Example:
            >>> lock = {"type": "less_than", "property_path": "attempt", "expected_value": 5}
            >>> result = self._check_termination_lock(lock, gate)
            >>> if result:
            ...     print(result.termination_type)  # "counter_upper_bound"
        """
        if not isinstance(lock, dict):
            return None

        lock_type = lock.get("type")
        expected_value = lock.get("expected_value")
        property_path = lock.get("property_path", "unknown")

        # Pattern 1: Counter with upper bound
        if lock_type in ["less_than", "less_than_or_equal"]:
            if isinstance(expected_value, (int, float)):
                return TerminationAnalysis(
                    has_termination=True,
                    termination_type="counter_upper_bound",
                    description=(
                        f"{lock_type} lock on '{property_path}' "
                        f"with limit {expected_value}"
                    ),
                    common_properties=[property_path] if isinstance(property_path, str) else [],
                    suggestions=[],
                )

        # Pattern 2: Counter with lower bound
        if lock_type in ["greater_than", "greater_than_or_equal"]:
            if isinstance(expected_value, (int, float)):
                return TerminationAnalysis(
                    has_termination=True,
                    termination_type="counter_lower_bound",
                    description=(
                        f"{lock_type} lock on '{property_path}' "
                        f"with limit {expected_value}"
                    ),
                    common_properties=[property_path] if isinstance(property_path, str) else [],
                    suggestions=[],
                )

        # Pattern 3: Range with boundaries
        if lock_type == "range":
            if isinstance(expected_value, list) and len(expected_value) == 2:
                min_val, max_val = expected_value
                if isinstance(min_val, (int, float)) and isinstance(max_val, (int, float)):
                    return TerminationAnalysis(
                        has_termination=True,
                        termination_type="range_boundary",
                        description=(
                            f"RANGE lock on '{property_path}' "
                            f"with bounds {expected_value}"
                        ),
                        common_properties=[property_path] if isinstance(property_path, str) else [],
                        suggestions=[],
                    )

        # Pattern 4: Finite state set - defer to complementary gate analysis
        # IN_LIST alone doesn't guarantee termination; need to check for complementary gates
        if lock_type == "in_list":
            return None  # Let complementary gate analysis handle this

        # No termination pattern detected in this lock
        return None

    def _report_infinite_cycle(self, cycle_path: list[str]) -> None:
        """
        Report a cycle with no exit path to final stage.

        This is a FATAL error as the cycle has no way to reach the final stage,
        creating a guaranteed infinite loop.

        Args:
            cycle_path: List of stage IDs forming the cycle
        """
        cycle_path_str = ' → '.join(cycle_path)

        self.issues.append(ConsistencyIssue(
            issue_type=ProcessIssueTypes.INFINITE_CYCLE,
            description=f"Infinite cycle detected with no path to final stage: {cycle_path_str}",
            stages=cycle_path,
            severity="fatal",
            details={
                "cycle_path": cycle_path,
                "message": (
                    "This cycle has no exit path and will loop forever. "
                    "Add a gate from one of the cycle stages to the final stage."
                )
            }
        ))

    def _report_uncontrolled_cycle(
        self, cycle_path: list[str], analysis: TerminationAnalysis
    ) -> None:
        """
        Report a cycle without clear termination condition.

        This is a WARNING as the cycle has an exit path but no detectable termination
        condition in the gate locks. The cycle might be safe, but we cannot verify it
        automatically.

        Args:
            cycle_path: List of stage IDs forming the cycle
            analysis: Termination analysis with suggestions for adding termination
        """
        cycle_path_str = ' → '.join(cycle_path)

        # Format suggestions as bulleted list
        suggestions_text = ""
        if analysis.suggestions:
            suggestions_text = "\n\nSuggestions:\n" + "\n".join(
                f"  {i+1}. {s}" for i, s in enumerate(analysis.suggestions)
            )

        self.issues.append(ConsistencyIssue(
            issue_type=ProcessIssueTypes.UNCONTROLLED_CYCLE,
            description=f"Uncontrolled cycle detected: {cycle_path_str}",
            stages=cycle_path,
            severity="warning",
            details={
                "cycle_path": cycle_path,
                "message": (
                    "This cycle has an exit path but no clear termination condition. "
                    "Ensure gate locks provide a way to break the cycle."
                    f"{suggestions_text}"
                ),
                "suggestions": analysis.suggestions,
            }
        ))

    def _report_controlled_cycle(
        self, cycle_path: list[str], analysis: TerminationAnalysis
    ) -> None:
        """
        Report a well-controlled cycle (optional, INFO level).

        This provides visibility into detected controlled cycles for users who
        want to understand their process structure. By default, this is not shown
        to avoid noise in the output.

        Args:
            cycle_path: List of stage IDs forming the cycle
            analysis: Termination analysis results showing why cycle is controlled
        """
        cycle_path_str = ' → '.join(cycle_path)

        self.issues.append(ConsistencyIssue(
            issue_type=ProcessIssueTypes.CONTROLLED_CYCLE,
            description=f"Controlled cycle detected: {cycle_path_str}",
            stages=cycle_path,
            severity="info",
            details={
                "cycle_path": cycle_path,
                "termination_type": analysis.termination_type,
                "termination_description": analysis.description,
                "common_properties": analysis.common_properties,
                "message": (
                    "This cycle is well-controlled and will terminate. No action needed."
                )
            }
        ))

    def _analyze_common_properties(self, cycle_gates: list[dict]) -> TerminationAnalysis:
        """
        Check if cycle gates share a common property with different requirements.

        This is the KEY INNOVATION of the controlled cycles feature. A common property
        across all gates with different lock requirements ensures the cycle will
        terminate in at least one stage.

        Examples of termination through common properties:
        - Counter: attempt < 5, attempt >= 5
        - Status: status == "processing", status == "completed"
        - Flag: has_more == true, has_more == false
        - Mixed: count < 10, count == 10 (different lock types)

        Args:
            cycle_gates: Gates that create or maintain the cycle

        Returns:
            TerminationAnalysis with detection results

        Example:
            >>> gates = [gate1, gate2]  # gate1 checks status=="A", gate2 checks status=="B"
            >>> analysis = self._analyze_common_properties(gates)
            >>> analysis.has_termination  # True
            >>> analysis.common_properties  # ["status"]
        """
        if not cycle_gates:
            return TerminationAnalysis(
                has_termination=False,
                termination_type="no_gates",
                description="No cycle gates to analyze",
                common_properties=[],
                suggestions=[]
            )

        # Step 1: Extract all properties checked by each gate's locks
        gate_properties: list[set[str]] = []
        for gate in cycle_gates:
            gate_props = set()
            locks = gate.get("locks", [])
            if not isinstance(locks, list):
                continue
            for lock in locks:
                # Extract property_path from lock if it exists
                prop_path = self._extract_property_path(lock)
                if prop_path:
                    gate_props.add(prop_path)
            gate_properties.append(gate_props)

        # Step 2: Find properties common to ALL gates
        if not gate_properties:
            return TerminationAnalysis(
                has_termination=False,
                termination_type="no_properties",
                description="No properties found in cycle gates",
                common_properties=[],
                suggestions=["Add locks with property_path to cycle gates"]
            )

        # Intersection of all gate property sets
        common_props = gate_properties[0].intersection(*gate_properties[1:])

        if not common_props:
            return TerminationAnalysis(
                has_termination=False,
                termination_type="no_common_properties",
                description="No properties common to all cycle gates",
                common_properties=[],
                suggestions=["Ensure all cycle gates check the same property with different requirements"]
            )

        # Step 3: For each common property, check if requirements differ across gates
        for prop in common_props:
            if self._property_has_varying_requirements(prop, cycle_gates):
                return TerminationAnalysis(
                    has_termination=True,
                    termination_type="common_property_variation",
                    description=(
                        f"Property '{prop}' has different requirements across cycle gates"
                    ),
                    common_properties=[prop],
                    suggestions=[]
                )

        return TerminationAnalysis(
            has_termination=False,
            termination_type="identical_requirements",
            description="Common properties found but all gates have identical requirements",
            common_properties=list(common_props),
            suggestions=["Ensure cycle gates have different requirements for common properties"]
        )

    def _extract_property_path(self, lock: dict) -> str | None:
        """
        Extract property_path from a lock, handling different lock types.

        Args:
            lock: Lock dictionary to extract property from

        Returns:
            Property path string if found, None otherwise
        """
        if not isinstance(lock, dict):
            return None

        # Simple locks have property_path attribute
        prop_path = lock.get("property_path")
        if isinstance(prop_path, str) and prop_path:
            return prop_path

        # Handle shorthand locks (e.g., "exists: property.path")
        if len(lock) == 1 and isinstance(list(lock.values())[0], str):
            return list(lock.values())[0]

        # CONDITIONAL locks: check if/then/else branches
        if lock.get("type") == "conditional":
            # For now, extract from condition locks
            # Could be enhanced to check then/else branches
            if_locks = lock.get("if", [])
            if isinstance(if_locks, list):
                for if_lock in if_locks:
                    prop = self._extract_property_path(if_lock)
                    if prop:
                        return prop

        # OR_LOGIC locks: check all paths
        if lock.get("type") == "or_logic":
            paths = lock.get("paths", [])
            if isinstance(paths, list):
                for path in paths:
                    if isinstance(path, dict) and "locks" in path:
                        path_locks = path["locks"]
                        if isinstance(path_locks, list):
                            for path_lock in path_locks:
                                prop = self._extract_property_path(path_lock)
                                if prop:
                                    return prop

        return None

    def _property_has_varying_requirements(
        self, property_path: str, gates: list[dict]
    ) -> bool:
        """
        Check if a property has different requirements across gates.

        Different requirements mean:
        - Different lock types (EQUALS vs LESS_THAN)
        - Different expected values (status == "A" vs status == "B")
        - Complementary conditions (flag == true vs flag == false)
        - Different bounds (count < 5 vs count >= 5)

        Args:
            property_path: Property to analyze
            gates: Gates to check

        Returns:
            True if requirements vary, ensuring termination

        Example:
            >>> # Gate 1: status == "processing", Gate 2: status == "completed"
            >>> self._property_has_varying_requirements("status", gates)
            True
        """
        # Collect all locks for this property across all gates
        property_locks: list[tuple[dict, dict]] = []
        for gate in gates:
            locks = gate.get("locks", [])
            if not isinstance(locks, list):
                continue
            for lock in locks:
                prop = self._extract_property_path(lock)
                if prop == property_path:
                    property_locks.append((gate, lock))

        if len(property_locks) < 2:
            return False  # Need at least 2 locks to have variation

        # Check for variations in lock requirements
        lock_signatures = []
        for _gate, lock in property_locks:
            # Create a signature for this lock's requirements
            signature = {
                'type': lock.get('type'),
                'expected_value': lock.get('expected_value')
            }
            lock_signatures.append(signature)

        # If all signatures are identical, no variation exists
        first_sig = lock_signatures[0]
        for sig in lock_signatures[1:]:
            if sig != first_sig:
                return True  # Found variation!

        return False

    def _analyze_individual_locks(self, cycle_gates: list[dict]) -> TerminationAnalysis:
        """Check individual locks for termination patterns."""
        for gate in cycle_gates:
            locks = gate.get("locks", [])
            if not isinstance(locks, list):
                continue
            for lock in locks:
                analysis = self._check_termination_lock(lock, gate)
                if analysis and analysis.has_termination:
                    return analysis
        return TerminationAnalysis(
            has_termination=False,
            termination_type="none",
            description="No individual lock termination patterns detected"
        )

    def _analyze_complementary_gates(self, cycle_gates: list[dict]) -> TerminationAnalysis:
        """
        Check if stages in cycle have complementary gates that provide exit.

        Complementary gates check the same property for opposite values:
        - Gate 1: has_more == true (continues cycle)
        - Gate 2: has_more == false (exits cycle)

        This ensures that the property value will eventually satisfy one gate or the other,
        providing a natural termination condition.

        Args:
            cycle_gates: Gates that create or maintain the cycle

        Returns:
            TerminationAnalysis with detection results

        Example:
            >>> # Stage has two gates: one for "should_retry == true", one for "should_retry == false"
            >>> analysis = self._analyze_complementary_gates(cycle_gates)
            >>> analysis.has_termination  # True
            >>> analysis.termination_type  # "complementary_boolean"
        """
        # Check for complementary boolean checks across all gates
        # Note: A full implementation would group by stage, but with dict format
        # we check all cycle gates together

        # For now, implement a simplified version that checks all cycle gates together
        # This is a limitation of the current dict-based approach
        # A full implementation would need stage context

        # Check for complementary boolean checks across all gates
        property_checks: dict[str, set[bool]] = {}

        for gate in cycle_gates:
            locks = gate.get("locks", [])
            if not isinstance(locks, list):
                continue

            for lock in locks:
                prop_path = self._extract_property_path(lock)
                if not prop_path:
                    continue

                # Check if it's an EQUALS lock with boolean value
                lock_type = lock.get("type")
                expected_value = lock.get("expected_value")

                if lock_type == "equals" and isinstance(expected_value, bool):
                    if prop_path not in property_checks:
                        property_checks[prop_path] = set()
                    property_checks[prop_path].add(expected_value)

        # Check if any property has both true and false checks
        for prop, values in property_checks.items():
            if len(values) >= 2:  # Has both true and false
                return TerminationAnalysis(
                    has_termination=True,
                    termination_type="complementary_boolean",
                    description=f"Complementary boolean gates on '{prop}'",
                    common_properties=[prop],
                    suggestions=[]
                )

        return TerminationAnalysis(
            has_termination=False,
            termination_type="no_complementary_gates",
            description="No complementary boolean gates found",
            common_properties=[],
            suggestions=self._generate_termination_suggestions(cycle_gates)
        )

    def _generate_termination_suggestions(self, cycle_gates: list[dict]) -> list[str]:
        """
        Generate helpful suggestions for adding termination conditions.

        Provides three common patterns for controlling cycles:
        1. Counter-based termination (iteration limit)
        2. Boolean flag termination (should_continue)
        3. Status progression termination (finite state machine)

        Args:
            cycle_gates: Gates in the cycle (for context, though not used in current implementation)

        Returns:
            List of actionable suggestions with YAML examples

        Example:
            >>> suggestions = self._generate_termination_suggestions(gates)
            >>> for suggestion in suggestions:
            ...     print(suggestion)
        """
        suggestions = []

        # Suggestion 1: Add an iteration counter
        suggestions.append(
            "Add an iteration counter with an upper bound:\n"
            "  locks:\n"
            "    - type: less_than\n"
            "      property_path: \"attempt\"\n"
            "      expected_value: 10\n"
            "      error_message: \"Maximum retry attempts exceeded\""
        )

        # Suggestion 2: Add complementary boolean gates
        suggestions.append(
            "Add complementary boolean gates:\n"
            "  continue_gate:\n"
            "    target_stage: next_processing\n"
            "    locks:\n"
            "      - type: equals\n"
            "        property_path: \"should_continue\"\n"
            "        expected_value: true\n"
            "  exit_gate:\n"
            "    target_stage: completed\n"
            "    locks:\n"
            "      - type: equals\n"
            "        property_path: \"should_continue\"\n"
            "        expected_value: false"
        )

        # Suggestion 3: Use status progression with finite states
        suggestions.append(
            "Use status progression with finite states:\n"
            "  continue_gate:\n"
            "    target_stage: processing\n"
            "    locks:\n"
            "      - type: in_list\n"
            "        property_path: \"status\"\n"
            "        expected_value: [\"pending\", \"processing\"]\n"
            "  complete_gate:\n"
            "    target_stage: final\n"
            "    locks:\n"
            "      - type: equals\n"
            "        property_path: \"status\"\n"
            "        expected_value: \"completed\""
        )

        return suggestions

    def _check_multiple_gates_same_target(self) -> None:
        """Check for multiple gates targeting the same stage within each stage."""
        stages = self.process_def.get("stages", {})
        if not isinstance(stages, dict):
            return

        for stage_name, stage in stages.items():
            if not isinstance(stage, dict):
                continue

            gates = stage.get("gates", {})
            if not isinstance(gates, dict):
                continue

            # Track target stages and gate names
            target_stages: list[str] = []
            gate_names: list[str] = []

            for gate_name, gate in gates.items():
                if not isinstance(gate, dict):
                    continue

                target_stage = gate.get("target_stage")
                if not isinstance(target_stage, str):
                    continue

                # Check if this target already exists
                if target_stage in target_stages:
                    # Find all gates with the same target
                    duplicate_gates = [
                        gate_names[i]
                        for i, target in enumerate(target_stages)
                        if target == target_stage
                    ]
                    duplicate_gates.append(gate_name)

                    issue = ConsistencyIssue(
                        issue_type=ProcessIssueTypes.MULTIPLE_GATES_SAME_TARGET,
                        description=(
                            f"Stage '{stage_name}' has multiple gates targeting the same stage '{target_stage}': "
                            f"{', '.join(duplicate_gates)}. Consider combining these gates into a single gate with multiple locks."
                        ),
                        stages=[stage_name],
                        severity="warning",
                    )
                    self.issues.append(issue)

                target_stages.append(target_stage)
                gate_names.append(gate_name)

    def _check_logical_conflicts(self) -> None:
        """Identify logical conflicts within gate conditions."""
        stages = self.process_def.get("stages", {})
        if not isinstance(stages, dict):
            return

        for stage_name, stage in stages.items():
            if not isinstance(stage, dict):
                continue

            gates = stage.get("gates", {})
            if not isinstance(gates, dict):
                continue

            for gate_name, gate in gates.items():
                if not isinstance(gate, dict):
                    continue

                locks = gate.get("locks", [])
                if not isinstance(locks, list):
                    continue

                # Group locks by property path
                locks_by_property: dict[str, list[dict]] = {}
                for lock in locks:
                    if not isinstance(lock, dict):
                        continue

                    # Extract property path from lock
                    prop_path = lock.get("property_path")
                    if isinstance(prop_path, str):
                        if prop_path not in locks_by_property:
                            locks_by_property[prop_path] = []
                        locks_by_property[prop_path].append(lock)

                # Check each property for conflicts
                for prop_path, prop_locks in locks_by_property.items():
                    conflict = self._detect_property_conflicts(prop_path, prop_locks)
                    if conflict:
                        issue = ConsistencyIssue(
                            issue_type=ProcessIssueTypes.LOGICAL_CONFLICT,
                            description=(
                                f"Gate '{gate_name}' in stage '{stage_name}' has conflicting conditions "
                                f"for property '{prop_path}': {conflict}"
                            ),
                            stages=[stage_name],
                            severity="warning",
                        )
                        self.issues.append(issue)

    def _detect_property_conflicts(self, prop_path: str, locks: list[dict]) -> str:
        """Detect logical conflicts between locks on the same property."""
        if len(locks) < 2:
            return ""  # No conflict possible with single lock

        # Check for EQUALS conflicts (multiple different expected values)
        equals_locks = [
            lock for lock in locks
            if lock.get("type") == "equals"
        ]
        if len(equals_locks) >= 2:
            values = [lock.get("expected_value") for lock in equals_locks]
            unique_values = {str(v) for v in values if v is not None}
            if len(unique_values) > 1:
                return f"Property must equal multiple different values: {', '.join(unique_values)}"

        # Check for GREATER_THAN + LESS_THAN conflicts (impossible range)
        greater_locks = [
            lock for lock in locks
            if lock.get("type") in ["greater_than", "greater_than_or_equal"]
        ]
        less_locks = [
            lock for lock in locks
            if lock.get("type") in ["less_than", "less_than_or_equal"]
        ]

        if greater_locks and less_locks:
            # Check if any combination creates an impossible condition
            for gt_lock in greater_locks:
                gt_value = gt_lock.get("expected_value")
                if not isinstance(gt_value, (int, float)):
                    continue

                for lt_lock in less_locks:
                    lt_value = lt_lock.get("expected_value")
                    if not isinstance(lt_value, (int, float)):
                        continue

                    # Check for impossible combinations
                    gt_type = gt_lock.get("type")
                    lt_type = lt_lock.get("type")

                    # Examples: value > 100 AND value < 50
                    if gt_type == "greater_than" and lt_type == "less_than":
                        if gt_value >= lt_value:
                            return f"Property must be > {gt_value} AND < {lt_value} (impossible)"
                    elif gt_type == "greater_than_or_equal" and lt_type == "less_than_or_equal":
                        if gt_value > lt_value:
                            return f"Property must be >= {gt_value} AND <= {lt_value} (impossible)"

                    # Also check if an EQUALS value is outside the range
                    for eq_lock in equals_locks:
                        eq_value = eq_lock.get("expected_value")
                        if isinstance(eq_value, (int, float)):
                            # Check if equals value conflicts with range
                            if gt_type == "greater_than" and eq_value <= gt_value:
                                return f"Property must equal {eq_value} AND be > {gt_value} (impossible)"
                            if lt_type == "less_than" and eq_value >= lt_value:
                                return f"Property must equal {eq_value} AND be < {lt_value} (impossible)"

        return ""  # No conflicts detected
