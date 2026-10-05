"""
Nexora Approval Manager
Scoped, expiring approvals for elevated actions
"""
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from nexora.backend.app.models import ApprovalStatus
from nexora.backend.app.schemas import ApprovalBase as ApprovalSchema


class ApprovalError(Exception):
    """Approval-related errors"""
    pass


@dataclass
class ApprovalRequest:
    """Request for approval"""
    run_id: str
    policy_decision_id: str
    scope_description: str
    expires_in_seconds: int = 300  # 5 minutes default


@dataclass
class ApprovalRecord:
    """Stored approval record"""
    id: str
    run_id: str
    policy_decision_id: str
    scope_description: str
    expires_at: datetime
    status: ApprovalStatus
    approver_id: Optional[str] = None
    decided_at: Optional[datetime] = None
    created_at: datetime = None


class ApprovalManager:
    """
    Approval Manager - handles scoped, expiring approvals.
    
    Key rules:
    - Approvals are scoped to ONE action
    - Approvals expire (default 5 minutes)
    - Silence is NEVER approval
    - Expired/rejected approval blocks the action
    - High-risk actions never auto-approved
    """
    
    def __init__(self, default_expiry_seconds: int = 300):
        self.default_expiry_seconds = default_expiry_seconds
        self._approvals: Dict[str, ApprovalRecord] = {}
    
    def request_approval(self, request: ApprovalRequest) -> ApprovalRecord:
        """
        Create a new approval request.
        
        Args:
            request: Approval request details
            
        Returns:
            Created approval record
        """
        approval_id = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(seconds=request.expires_in_seconds)
        
        record = ApprovalRecord(
            id=approval_id,
            run_id=request.run_id,
            policy_decision_id=request.policy_decision_id,
            scope_description=request.scope_description,
            expires_at=expires_at,
            status=ApprovalStatus.PENDING,
            created_at=datetime.now(),
        )
        
        self._approvals[approval_id] = record
        return record
    
    def get_approval(self, approval_id: str) -> Optional[ApprovalRecord]:
        """Get approval by ID"""
        return self._approvals.get(approval_id)
    
    def get_pending_for_run(self, run_id: str) -> List[ApprovalRecord]:
        """Get all pending approvals for a run"""
        return [
            a for a in self._approvals.values()
            if a.run_id == run_id and a.status == ApprovalStatus.PENDING
        ]
    
    def decide(
        self,
        approval_id: str,
        approve: bool,
        approver_id: str,
    ) -> ApprovalRecord:
        """
        Record approval decision.
        
        Args:
            approval_id: Approval to decide
            approve: True to approve, False to reject
            approver_id: ID of approver
            
        Returns:
            Updated approval record
            
        Raises:
            ApprovalError: If approval not found or already decided
        """
        record = self._approvals.get(approval_id)
        if not record:
            raise ApprovalError(f"Approval not found: {approval_id}")
        
        if record.status != ApprovalStatus.PENDING:
            raise ApprovalError(f"Approval already decided: {record.status.value}")
        
        # Check expiry
        if datetime.now() > record.expires_at:
            record.status = ApprovalStatus.EXPIRED
            record.decided_at = datetime.now()
            raise ApprovalError("Approval has expired")
        
        if approve:
            record.status = ApprovalStatus.APPROVED
        else:
            record.status = ApprovalStatus.REJECTED
        
        record.approver_id = approver_id
        record.decided_at = datetime.now()
        
        return record
    
    def check_expired(self) -> List[ApprovalRecord]:
        """Check and mark expired approvals"""
        now = datetime.now()
        expired = []
        
        for record in self._approvals.values():
            if record.status == ApprovalStatus.PENDING and now > record.expires_at:
                record.status = ApprovalStatus.EXPIRED
                record.decided_at = now
                expired.append(record)
        
        return expired
    
    def is_approved(self, approval_id: str) -> bool:
        """Check if approval was granted and not expired"""
        record = self._approvals.get(approval_id)
        if not record:
            return False
        
        if record.status != ApprovalStatus.APPROVED:
            return False
        
        # Double-check expiry
        if datetime.now() > record.expires_at:
            record.status = ApprovalStatus.EXPIRED
            return False
        
        return True
    
    def get_approval_state(self, policy_decision_id: str) -> Optional[str]:
        """Get approval state for a policy decision"""
        for record in self._approvals.values():
            if record.policy_decision_id == policy_decision_id:
                if record.status == ApprovalStatus.PENDING:
                    if datetime.now() > record.expires_at:
                        return "expired"
                    return "pending"
                return record.status.value
        return None
    
    def to_schema(self, record: ApprovalRecord) -> ApprovalSchema:
        """Convert to API schema"""
        return ApprovalSchema(
            id=record.id,
            run_id=record.run_id,
            policy_decision_id=record.policy_decision_id,
            scope_description=record.scope_description,
            expires_at=record.expires_at,
            status=record.status,
            approver_id=record.approver_id,
            decided_at=record.decided_at,
            created_at=record.created_at,
        )


# Global instance
_approval_manager: Optional[ApprovalManager] = None


def get_approval_manager() -> ApprovalManager:
    """Get or create approval manager"""
    global _approval_manager
    if _approval_manager is None:
        _approval_manager = ApprovalManager()
    return _approval_manager
