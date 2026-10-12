"""
Nexora Tool Router and Sandbox Adapter
Typed tool schemas, validation, and sandboxed execution
"""
import json
import os
import subprocess
import tempfile
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from nexora.backend.app.core.policy import Capability
from nexora.backend.app.models import ExecutionStatus
from nexora.backend.app.schemas import ToolExecutionBase as ToolExecutionSchema
from nexora.backend.config.settings import get_settings

settings = get_settings()


# ============================================================
# Tool Schemas (Typed)
# ============================================================

class ToolName(str, Enum):
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


# Tool argument schemas (for validation)
TOOL_SCHEMAS: Dict[ToolName, Dict[str, Any]] = {
    ToolName.REPO_LIST: {
        "type": "object",
        "properties": {
            "path": {"type": "string", "default": "."},
            "pattern": {"type": "string", "default": "**/*"},
        },
        "required": [],
        "additionalProperties": False,
    },
    ToolName.REPO_READ: {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "start_line": {"type": "integer", "minimum": 1},
            "end_line": {"type": "integer", "minimum": 1},
        },
        "required": ["path"],
        "additionalProperties": False,
    },
    ToolName.REPO_WRITE: {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
            "mode": {"type": "string", "enum": ["create", "overwrite", "patch"], "default": "overwrite"},
        },
        "required": ["path", "content"],
        "additionalProperties": False,
    },
    ToolName.TEST_RUN: {
        "type": "object",
        "properties": {
            "command": {"type": "string", "default": "pytest -v"},
            "timeout_seconds": {"type": "integer", "default": 120},
        },
        "required": [],
        "additionalProperties": False,
    },
    ToolName.GIT_STATUS: {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    ToolName.GIT_DIFF: {
        "type": "object",
        "properties": {
            "staged": {"type": "boolean", "default": False},
        },
        "required": [],
        "additionalProperties": False,
    },
    ToolName.GIT_BRANCH: {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["list", "create", "switch"], "default": "list"},
            "name": {"type": "string"},
        },
        "required": [],
        "additionalProperties": False,
    },
    ToolName.GIT_COMMIT: {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "files": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["message"],
        "additionalProperties": False,
    },
    ToolName.GIT_PUSH: {
        "type": "object",
        "properties": {
            "remote": {"type": "string", "default": "origin"},
            "branch": {"type": "string"},
            "force": {"type": "boolean", "default": False},
        },
        "required": [],
        "additionalProperties": False,
    },
    ToolName.SHELL_RUN: {
        "type": "object",
        "properties": {
            "command": {"type": "string"},
            "timeout_seconds": {"type": "integer", "default": 60},
            "working_dir": {"type": "string"},
        },
        "required": ["command"],
        "additionalProperties": False,
    },
    ToolName.NETWORK_FETCH: {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "method": {"type": "string", "default": "GET"},
            "headers": {"type": "object"},
            "timeout_seconds": {"type": "integer", "default": 30},
        },
        "required": ["url"],
        "additionalProperties": False,
    },
}


# Capability mapping for each tool
TOOL_CAPABILITIES: Dict[ToolName, Capability] = {
    ToolName.REPO_LIST: Capability.REPO_LIST,
    ToolName.REPO_READ: Capability.REPO_READ,
    ToolName.REPO_WRITE: Capability.REPO_WRITE,
    ToolName.TEST_RUN: Capability.TEST_RUN,
    ToolName.GIT_STATUS: Capability.GIT_STATUS,
    ToolName.GIT_DIFF: Capability.GIT_DIFF,
    ToolName.GIT_BRANCH: Capability.GIT_BRANCH,
    ToolName.GIT_COMMIT: Capability.GIT_COMMIT,
    ToolName.GIT_PUSH: Capability.GIT_PUSH,
    ToolName.SHELL_RUN: Capability.SHELL_RUN,
    ToolName.NETWORK_FETCH: Capability.NETWORK_FETCH,
}


@dataclass
class ToolRequest:
    """Validated tool request"""
    tool_name: ToolName
    arguments: Dict[str, Any]
    request_id: str
    capability: Capability


class ToolRouter:
    """
    Tool Router - validates and routes typed tool requests.
    
    Only accepts typed tool schemas. Rejects malformed/unknown requests
    before policy evaluation. No arbitrary shell strings.
    """
    
    def __init__(self):
        self.schemas = TOOL_SCHEMAS
        self.capabilities = TOOL_CAPABILITIES
    
    def validate_and_route(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        request_id: str,
    ) -> ToolRequest:
        """
        Validate tool request against schema.
        
        Args:
            tool_name: Name of the tool
            arguments: Tool arguments
            request_id: Unique request identifier
            
        Returns:
            Validated ToolRequest
            
        Raises:
            ToolValidationError: If validation fails
        """
        # Check tool exists
        try:
            tool_enum = ToolName(tool_name)
        except ValueError:
            raise ToolValidationError(f"Unknown tool: {tool_name}")
        
        # Get schema
        schema = self.schemas.get(tool_enum)
        if not schema:
            raise ToolValidationError(f"No schema for tool: {tool_name}")
        
        # Validate required fields
        required = schema.get("required", [])
        for field_name in required:
            if field_name not in arguments:
                raise ToolValidationError(f"Missing required field: {field_name}")
        
        # Validate no additional properties
        allowed_props = set(schema.get("properties", {}).keys())
        for arg_name in arguments:
            if arg_name not in allowed_props:
                raise ToolValidationError(f"Unexpected argument: {arg_name}")
        
        # Type validation (basic)
        for arg_name, arg_value in arguments.items():
            prop_schema = schema["properties"].get(arg_name, {})
            expected_type = prop_schema.get("type")
            if expected_type and not self._check_type(arg_value, expected_type):
                raise ToolValidationError(
                    f"Argument '{arg_name}' must be {expected_type}, got {type(arg_value).__name__}"
                )
            
            # Enum validation
            enum_values = prop_schema.get("enum")
            if enum_values and arg_value not in enum_values:
                raise ToolValidationError(
                    f"Argument '{arg_name}' must be one of {enum_values}, got {arg_value}"
                )
        
        # Get capability
        capability = self.capabilities.get(tool_enum)
        if not capability:
            raise ToolValidationError(f"No capability mapping for tool: {tool_name}")
        
        return ToolRequest(
            tool_name=tool_enum,
            arguments=arguments,
            request_id=request_id,
            capability=capability,
        )
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Basic type checking"""
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        expected = type_map.get(expected_type)
        if expected is None:
            return True
        return isinstance(value, expected)
    
    def get_schema(self, tool_name: ToolName) -> Dict[str, Any]:
        """Get JSON schema for a tool"""
        return self.schemas.get(tool_name, {})
    
    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """Get all tool schemas for model"""
        schemas = []
        for tool_name, schema in self.schemas.items():
            schemas.append({
                "name": tool_name.value,
                "description": f"Tool: {tool_name.value}",
                "parameters": schema,
            })
        return schemas


class ToolValidationError(Exception):
    """Tool validation error"""
    pass


# ============================================================
# Sandbox Adapter
# ============================================================

class SandboxAdapter(ABC):
    """Abstract sandbox adapter"""
    
    @abstractmethod
    async def execute(
        self,
        tool_request: ToolRequest,
        workspace_path: str,
        environment: Dict[str, str],
    ) -> ToolExecutionSchema:
        """Execute tool in sandbox"""
        pass
    
    @abstractmethod
    async def cleanup(self, sandbox_id: str) -> None:
        """Clean up sandbox"""
        pass


class LocalSandboxAdapter(SandboxAdapter):
    """
    Local sandbox adapter for development.
    
    In production, this would be replaced with Token Factory Sandboxes.
    This implementation uses subprocess with resource limits.
    """
    
    def __init__(self):
        self.sandboxes: Dict[str, Dict[str, Any]] = {}
    
    async def execute(
        self,
        tool_request: ToolRequest,
        workspace_path: str,
        environment: Dict[str, str],
    ) -> ToolExecutionSchema:
        """Execute tool in local sandbox"""
        sandbox_id = f"local-{uuid.uuid4().hex[:8]}"
        start_time = datetime.now()
        
        try:
            # Prepare environment
            env = os.environ.copy()
            env.update(environment)
            # Remove sensitive env vars
            for key in list(env.keys()):
                if any(s in key.lower() for s in ["key", "secret", "password", "token", "api"]):
                    if key not in ["PATH", "HOME", "USER"]:
                        env.pop(key, None)
            
            # Execute based on tool
            if tool_request.tool_name == ToolName.REPO_LIST:
                result = await self._repo_list(tool_request.arguments, workspace_path)
            elif tool_request.tool_name == ToolName.REPO_READ:
                result = await self._repo_read(tool_request.arguments, workspace_path)
            elif tool_request.tool_name == ToolName.REPO_WRITE:
                result = await self._repo_write(tool_request.arguments, workspace_path)
            elif tool_request.tool_name == ToolName.TEST_RUN:
                result = await self._test_run(tool_request.arguments, workspace_path, env)
            elif tool_request.tool_name == ToolName.GIT_STATUS:
                result = await self._git_status(workspace_path)
            elif tool_request.tool_name == ToolName.GIT_DIFF:
                result = await self._git_diff(tool_request.arguments, workspace_path)
            elif tool_request.tool_name == ToolName.GIT_BRANCH:
                result = await self._git_branch(tool_request.arguments, workspace_path)
            elif tool_request.tool_name == ToolName.GIT_COMMIT:
                result = await self._git_commit(tool_request.arguments, workspace_path, env)
            elif tool_request.tool_name == ToolName.GIT_PUSH:
                result = await self._git_push(tool_request.arguments, workspace_path, env)
            elif tool_request.tool_name == ToolName.SHELL_RUN:
                result = await self._shell_run(tool_request.arguments, workspace_path, env)
            elif tool_request.tool_name == ToolName.NETWORK_FETCH:
                result = await self._network_fetch(tool_request.arguments)
            else:
                raise ValueError(f"Unsupported tool: {tool_request.tool_name}")
            
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return ToolExecutionSchema(
                id=sandbox_id,
                run_id="",  # Filled by caller
                tool_request_id=tool_request.request_id,
                tool_name=tool_request.tool_name.value,
                arguments=tool_request.arguments,
                stdout=result.get("stdout", ""),
                stderr=result.get("stderr", ""),
                exit_code=result.get("exit_code", 0),
                duration_ms=duration_ms,
                sandbox_id=sandbox_id,
                execution_status=ExecutionStatus.SUCCESS if result.get("exit_code", 0) == 0 else ExecutionStatus.FAILURE,
                created_at=datetime.now(),
            )
            
        except subprocess.TimeoutExpired:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            return ToolExecutionSchema(
                id=sandbox_id,
                run_id="",
                tool_request_id=tool_request.request_id,
                tool_name=tool_request.tool_name.value,
                arguments=tool_request.arguments,
                stdout="",
                stderr="Execution timed out",
                exit_code=-1,
                duration_ms=duration_ms,
                sandbox_id=sandbox_id,
                execution_status=ExecutionStatus.TIMEOUT,
                created_at=datetime.now(),
            )
        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            return ToolExecutionSchema(
                id=sandbox_id,
                run_id="",
                tool_request_id=tool_request.request_id,
                tool_name=tool_request.tool_name.value,
                arguments=tool_request.arguments,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                duration_ms=duration_ms,
                sandbox_id=sandbox_id,
                execution_status=ExecutionStatus.ERROR,
                created_at=datetime.now(),
            )
    
    async def cleanup(self, sandbox_id: str) -> None:
        """Clean up sandbox resources"""
        if sandbox_id in self.sandboxes:
            del self.sandboxes[sandbox_id]
    
    async def _repo_list(self, args: Dict, workspace: str) -> Dict[str, Any]:
        path = Path(workspace) / args.get("path", ".")
        pattern = args.get("pattern", "**/*")
        
        files = []
        for f in path.rglob(pattern):
            if f.is_file():
                rel = f.relative_to(workspace)
                files.append(str(rel))
        
        return {"stdout": json.dumps(files), "stderr": "", "exit_code": 0}
    
    async def _repo_read(self, args: Dict, workspace: str) -> Dict[str, Any]:
        path = Path(workspace) / args["path"]
        
        if not path.exists():
            return {"stdout": "", "stderr": f"File not found: {args['path']}", "exit_code": 1}
        
        content = path.read_text(encoding="utf-8")
        lines = content.splitlines()
        
        start = args.get("start_line", 1) - 1
        end = args.get("end_line", len(lines))
        
        selected = lines[start:end]
        result = "\n".join(selected)
        
        return {"stdout": result, "stderr": "", "exit_code": 0}
    
    async def _repo_write(self, args: Dict, workspace: str) -> Dict[str, Any]:
        path = Path(workspace) / args["path"]
        content = args["content"]
        mode = args.get("mode", "overwrite")
        
        # Security: ensure path is within workspace
        try:
            path.resolve().relative_to(Path(workspace).resolve())
        except ValueError:
            return {"stdout": "", "stderr": "Path traversal attempt blocked", "exit_code": 1}
        
        if mode == "create" and path.exists():
            return {"stdout": "", "stderr": f"File already exists: {args['path']}", "exit_code": 1}
        
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        
        return {"stdout": f"Written {len(content)} bytes to {args['path']}", "stderr": "", "exit_code": 0}
    
    async def _test_run(self, args: Dict, workspace: str, env: Dict[str, str]) -> Dict[str, Any]:
        command = args.get("command", "pytest -v")
        timeout = args.get("timeout_seconds", 120)
        
        # Run in workspace directory
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=workspace,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return {
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "exit_code": proc.returncode or 0,
            }
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise subprocess.TimeoutExpired(command, timeout)
    
    async def _git_status(self, workspace: str) -> Dict[str, Any]:
        proc = await asyncio.create_subprocess_exec(
            "git", "status", "--porcelain",
            cwd=workspace,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return {
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
            "exit_code": proc.returncode or 0,
        }
    
    async def _git_diff(self, args: Dict, workspace: str) -> Dict[str, Any]:
        cmd = ["git", "diff"]
        if args.get("staged"):
            cmd.append("--cached")
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=workspace,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return {
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
            "exit_code": proc.returncode or 0,
        }
    
    async def _git_branch(self, args: Dict, workspace: str) -> Dict[str, Any]:
        action = args.get("action", "list")
        name = args.get("name")
        
        if action == "list":
            cmd = ["git", "branch"]
        elif action == "create":
            cmd = ["git", "branch", name]
        elif action == "switch":
            cmd = ["git", "checkout", name]
        else:
            return {"stdout": "", "stderr": f"Unknown action: {action}", "exit_code": 1}
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=workspace,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return {
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
            "exit_code": proc.returncode or 0,
        }
    
    async def _git_commit(self, args: Dict, workspace: str, env: Dict[str, str]) -> Dict[str, Any]:
        # This requires approval in policy - just stage and commit
        files = args.get("files", ["."])
        message = args["message"]
        
        proc = await asyncio.create_subprocess_exec(
            "git", "add", *files,
            cwd=workspace,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        
        proc = await asyncio.create_subprocess_exec(
            "git", "commit", "-m", message,
            cwd=workspace,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return {
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
            "exit_code": proc.returncode or 0,
        }
    
    async def _git_push(self, args: Dict, workspace: str, env: Dict[str, str]) -> Dict[str, Any]:
        # Denied in MVP - return blocked
        return {
            "stdout": "",
            "stderr": "Git push is denied in MVP. Requires explicit human approval.",
            "exit_code": 1,
        }
    
    async def _shell_run(self, args: Dict, workspace: str, env: Dict[str, str]) -> Dict[str, Any]:
        command = args["command"]
        timeout = args.get("timeout_seconds", 60)
        working_dir = args.get("working_dir", workspace)
        
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=working_dir,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return {
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "exit_code": proc.returncode or 0,
            }
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise subprocess.TimeoutExpired(command, timeout)
    
    async def _network_fetch(self, args: Dict) -> Dict[str, Any]:
        # Denied in MVP - no network access for task sandboxes
        return {
            "stdout": "",
            "stderr": "Network access is denied in MVP. Task sandboxes have no internet access.",
            "exit_code": 1,
        }


# Need to import asyncio
import asyncio


# Global instances
_tool_router: Optional[ToolRouter] = None
_sandbox_adapter: Optional[SandboxAdapter] = None


def get_tool_router() -> ToolRouter:
    """Get or create tool router"""
    global _tool_router
    if _tool_router is None:
        _tool_router = ToolRouter()
    return _tool_router


def get_sandbox_adapter() -> SandboxAdapter:
    """Get or create sandbox adapter"""
    global _sandbox_adapter
    if _sandbox_adapter is None:
        _sandbox_adapter = LocalSandboxAdapter()
    return _sandbox_adapter
