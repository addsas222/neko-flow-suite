"""flow_simplify 共享层：证明记录、只读发现与覆盖率地图。"""

from .discovery import Discovery, Finding, discover, record_from_finding
from .errors import AuthorityError, ScopeError, SimplifyError
from .proof import ProofLedger, ProofRecord, rank
from .scan import Candidate, ScanReport
from .scan_report import scan_repository, tree_summary

__all__ = [
    "AuthorityError",
    "Candidate",
    "Discovery",
    "Finding",
    "ProofLedger",
    "ProofRecord",
    "ScopeError",
    "ScanReport",
    "SimplifyError",
    "discover",
    "rank",
    "record_from_finding",
    "scan_repository",
    "tree_summary",
]
