"""
Nexora Policy Engine
Deterministic policy evaluation with fail-closed behavior
"""
import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

from nexora.backend.app.models import PolicyDecision as PolicyDecisionEnum
from nexora.backend.app.schemas import PolicyDecisionBase as PolicyDecisionSchema
from nexora.backend.config.settings import get_settings

settings = get_settings()


class Capability(str, Enum):
    """Defined capabilities that tools can require"""
    REPO_LIST = "repo.list"
    REPO_READ = "repo.read"
    REPO_WRITE = "repo.write"
    TEST_RUN = "test.run"
    GIT_STATUS = "git.status"
    GIT_DIFF = "git.diff"
    GIT_BRANCH = "git.branch"
    GIT_COMMIT = "git.commit"
    GIT_PUSH = "git.push"
    SHELL_RUN = "shell.run"
    NETWORK_FETCH = "network.fetch"


# Protected paths that can never be written
PROTECTED_PATHS: Set[str] = {
    ".env",
    ".env.*",
    "*.key",
    "*.pem",
    "*.p12",
    "*.pfx",
    "id_rsa",
    "id_ed25519",
    "authorized_keys",
    "config/policies.yaml",
    "config/policies/*.yaml",
    "*.sql",
    "migrations/*",
}

# Protected commands that are always denied
DENIED_COMMANDS: Set[str] = {
    "rm -rf",
    "rm -rf /",
    "dd",
    "mkfs",
    "fdisk",
    "shutdown",
    "reboot",
    "curl",
    "wget",
    "nc",
    "netcat",
    "ssh",
    "scp",
    "rsync",
    "git push",
    "git push --force",
    "git push -f",
}

# Allowed commands (for demo profile)
ALLOWED_COMMANDS_DEMO: Set[str] = {
    "python",
    "python3",
    "pytest",
    "pip",
    "pip3",
    "cat",
    "ls",
    "find",
    "grep",
    "head",
    "tail",
    "wc",
    "diff",
    "patch",
    "git status",
    "git diff",
    "git log",
    "git branch",
    "git show",
}


@dataclass
class PolicyRule:
    """A single policy rule"""
    capability: Capability
    decision: PolicyDecisionEnum
    reason_codes: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyConfig:
    """Loaded policy configuration"""
    version: str
    rules: List[PolicyRule] = field(default_factory=list)
    default_decision: PolicyDecisionEnum = PolicyDecisionEnum.DENY
    protected_paths: Set[str] = field(default_factory=set)
    denied_commands: Set[str] = field(default_factory=set)
    allowed_commands: Set[str] = field(default_factory=set)
    approval_required_capabilities: Set[Capability] = field(default_factory=set)
    monitoring_capabilities: Set[Capability] = field(default_factory=set)


class PolicyEngine:
    """
    Deterministic Policy Engine
    
    Evaluates tool requests against versioned policy rules.
    Fail-closed: unknown capabilities, malformed arguments, policy errors -> DENY
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self._engine_version = "1.0.0"
    
    def _load_config(self, config_path: Optional[str]) -> PolicyConfig:
        """Load policy configuration from YAML file"""
        if config_path is None:
            # policy.py lives in backend/app/core, policies.yaml in
            # backend/config -- two levels up, not one. The wrong depth
            # resolved to backend/app/config/policies.yaml, which does not
            # exist, so the FileNotFoundError fallback silently dropped every
            # rule and failed every capability closed on DEFAULT_DENY.
            config_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "config",
                "policies.yaml"
            )
        
        config = PolicyConfig(version="1.0.0")
        
        try:
            with open(config_path, "r", encoding="utf-8-sig") as f:
                data = yaml.safe_load(f) or {}
            
            config.version = data.get("version", "1.0.0")
            config.default_decision = PolicyDecisionEnum(data.get("default_decision", "DENY"))
            
            # Load protected paths
            config.protected_paths = set(PROTECTED_PATHS)
            config.protected_paths.update(data.get("protected_paths", []))
            
            # Load denied commands
            config.denied_commands = set(DENIED_COMMANDS)
            config.denied_commands.update(data.get("denied_commands", []))
            
            # Load allowed commands
            config.allowed_commands = set(ALLOWED_COMMANDS_DEMO)
            config.allowed_commands.update(data.get("allowed_commands", []))
            
            # Load approval-required capabilities
            config.approval_required_capabilities = {
                Capability(c) for c in data.get("approval_required_capabilities", [
                    "git.commit",
                    "git.push",
                    "shell.run",
                    "network.fetch",
                ])
            }
            
            # Load monitoring capabilities
            config.monitoring_capabilities = {
                Capability(c) for c in data.get("monitoring_capabilities", [
                    "repo.write",
                    "test.run",
                ])
            }
            
            # Load rules
            for rule_data in data.get("rules", []):
                try:
                    capability = Capability(rule_data["capability"])
                    decision = PolicyDecisionEnum(rule_data["decision"])
                    config.rules.append(PolicyRule(
                        capability=capability,
                        decision=decision,
                        reason_codes=rule_data.get("reason_codes", []),
                        conditions=rule_data.get("conditions", {}),
                    ))
                except (KeyError, ValueError) as e:
                    # Skip invalid rules but log in production
                    continue
                    
        except FileNotFoundError:
            # Use defaults if config file doesn't exist
            config.approval_required_capabilities = {
                Capability.GIT_COMMIT,
                Capability.GIT_PUSH,
                Capability.SHELL_RUN,
                Capability.NETWORK_FETCH,
            }
            config.monitoring_capabilities = {
                Capability.REPO_WRITE,
                Capability.TEST_RUN,
            }
        
        return config
    
    def evaluate(
        self,
        capability: Capability,
        normalized_arguments: Dict[str, Any],
        target_path: Optional[str] = None,
        risk_level: str = "medium",
        runtime_state: Optional[Dict[str, Any]] = None,
        approval_state: Optional[str] = None,
    ) -> PolicyDecisionSchema:
        """
        Evaluate a tool request against policy.
        
        This is the core security boundary - every tool request passes here.
        """
        # 1. Validate capability is known
        try:
            capability_enum = Capability(capability) if isinstance(capability, str) else capability
        except ValueError:
            return PolicyDecisionSchema(
                capability=str(capability),
                decision=PolicyDecisionEnum.DENY,
                reason_codes=["UNKNOWN_CAPABILITY"],
                risk_level="critical",
                normalized_arguments=normalized_arguments,
                target_path=target_path,
                policy_version=self.config.version,
                engine_version=self._engine_version,
            )
        
        # 2. Check for protected path access
        if target_path and self._is_protected_path(target_path):
            return PolicyDecisionSchema(
                capability=capability_enum.value,
                decision=PolicyDecisionEnum.DENY,
                reason_codes=["PROTECTED_PATH_ACCESS"],
                risk_level="critical",
                normalized_arguments=normalized_arguments,
                target_path=target_path,
                policy_version=self.config.version,
                engine_version=self._engine_version,
            )
        
        # 3. Check for denied commands
        if capability_enum == Capability.SHELL_RUN:
            command = normalized_arguments.get("command", "")
            if self._is_denied_command(command):
                return PolicyDecisionSchema(
                    capability=capability_enum.value,
                    decision=PolicyDecisionEnum.DENY,
                    reason_codes=["DENIED_COMMAND"],
                    risk_level="critical",
                    normalized_arguments=normalized_arguments,
                    target_path=target_path,
                    policy_version=self.config.version,
                    engine_version=self._engine_version,
                )
        
        # 4. Check explicit rules
        for rule in self.config.rules:
            if rule.capability == capability_enum:
                if self._match_conditions(rule.conditions, normalized_arguments, runtime_state):
                    return PolicyDecisionSchema(
                        capability=capability_enum.value,
                        decision=rule.decision,
                        reason_codes=rule.reason_codes or ["RULE_MATCH"],
                        risk_level=risk_level,
                        normalized_arguments=normalized_arguments,
                        target_path=target_path,
                        policy_version=self.config.version,
                        engine_version=self._engine_version,
                    )
        
        # 5. Check if approval required
        if capability_enum in self.config.approval_required_capabilities:
            if approval_state == "approved":
                return PolicyDecisionSchema(
                    capability=capability_enum.value,
                    decision=PolicyDecisionEnum.ALLOW,
                    reason_codes=["APPROVED"],
                    risk_level=risk_level,
                    normalized_arguments=normalized_arguments,
                    target_path=target_path,
                    policy_version=self.config.version,
                    engine_version=self._engine_version,
                )
            elif approval_state == "pending":
                return PolicyDecisionSchema(
                    capability=capability_enum.value,
                    decision=PolicyDecisionEnum.REQUIRE_APPROVAL,
                    reason_codes=["REQUIRES_APPROVAL"],
                    risk_level=risk_level,
                    normalized_arguments=normalized_arguments,
                    target_path=target_path,
                    policy_version=self.config.version,
                    engine_version=self._engine_version,
                )
            else:
                return PolicyDecisionSchema(
                    capability=capability_enum.value,
                    decision=PolicyDecisionEnum.REQUIRE_APPROVAL,
                    reason_codes=["REQUIRES_APPROVAL"],
                    risk_level=risk_level,
                    normalized_arguments=normalized_arguments,
                    target_path=target_path,
                    policy_version=self.config.version,
                    engine_version=self._engine_version,
                )
        
        # 6. Check if monitoring required
        if capability_enum in self.config.monitoring_capabilities:
            return PolicyDecisionSchema(
                capability=capability_enum.value,
                decision=PolicyDecisionEnum.ALLOW_WITH_MONITORING,
                reason_codes=["MONITORED"],
                risk_level=risk_level,
                normalized_arguments=normalized_arguments,
                target_path=target_path,
                policy_version=self.config.version,
                engine_version=self._engine_version,
            )
        
        # 7. Default decision (fail closed)
        return PolicyDecisionSchema(
            capability=capability_enum.value,
            decision=self.config.default_decision,
            reason_codes=["DEFAULT_DENY"],
            risk_level=risk_level,
            normalized_arguments=normalized_arguments,
            target_path=target_path,
            policy_version=self.config.version,
            engine_version=self._engine_version,
        )
    
    def _is_protected_path(self, path: str) -> bool:
        """Check if path matches protected patterns"""
        path_obj = Path(path)
        for pattern in self.config.protected_paths:
            if path_obj.match(pattern) or path == pattern:
                return True
            # Check parent directories
            for parent in path_obj.parents:
                if parent.match(pattern) or str(parent) == pattern:
                    return True
        return False
    
    def _is_denied_command(self, command: str) -> bool:
        """Check if command matches denied patterns"""
        command_lower = command.lower().strip()
        for denied in self.config.denied_commands:
            if denied.lower() in command_lower:
                return True
        return False
    
    def _match_conditions(
        self,
        conditions: Dict[str, Any],
        arguments: Dict[str, Any],
        runtime_state: Optional[Dict[str, Any]],
    ) -> bool:
        """Check if rule conditions match"""
        if not conditions:
            return True
        
        for key, expected in conditions.items():
            if key == "risk_level":
                actual = arguments.get("risk_level", "medium")
                if actual != expected:
                    return False
            elif key == "path_prefix":
                target = arguments.get("path", "")
                if not target.startswith(expected):
                    return False
            elif runtime_state and key in runtime_state:
                if runtime_state[key] != expected:
                    return False
            elif arguments.get(key) != expected:
                return False
        return True


# Global policy engine instance
_policy_engine: Optional[PolicyEngine] = None


def get_policy_engine() -> PolicyEngine:
    """Get or create the global policy engine instance"""
    global _policy_engine
    if _policy_engine is None:
        _policy_engine = PolicyEngine()
    return _policy_engine
